import csv
import io
import time
import json
import re
from functools import wraps
from flask import Blueprint, render_template, request, redirect, url_for, session, flash, Response, jsonify
from db import query_all, query_one, execute_stmt, get_db
from table_service import (
    ALL_TABLES, ALL_VIEWS, get_table_schema, get_fk_options_for_table,
    get_table_data, insert_row, update_row, delete_row
)

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")


def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get("is_admin"):
            flash("Admin password required.", "warning")
            return redirect(url_for("learner.dashboard"))

        # Inactivity check (30 minutes = 1800s)
        last_act = session.get("admin_last_activity", 0)
        if last_act and (time.time() - last_act > 1800):
            session["is_admin"] = False
            session.pop("admin_last_activity", None)
            flash("Admin mode session expired due to 30 minutes of inactivity.", "info")
            return redirect(url_for("learner.dashboard"))

        session["admin_last_activity"] = time.time()
        return f(*args, **kwargs)
    return decorated_function


@admin_bp.route("")
@admin_required
def admin_root():
    return redirect(url_for("admin.dashboard"))


# -----------------------------------------------------------------------------
# 1. ADMIN DASHBOARD
# -----------------------------------------------------------------------------
@admin_bp.route("/dashboard")
@admin_required
def dashboard():
    # 6 KPIs
    user_count = query_one("SELECT COUNT(*) AS c FROM users")["c"]
    course_count = query_one("SELECT COUNT(*) AS c FROM courses WHERE status = 'published'")["c"]
    enrol_count = query_one("SELECT COUNT(*) AS c FROM enrolments")["c"]
    
    # Status breakdown
    completed_count = query_one("SELECT COUNT(*) AS c FROM enrolments WHERE status = 'completed'")["c"]
    active_count = query_one("SELECT COUNT(*) AS c FROM enrolments WHERE status = 'active'")["c"]
    dropped_count = query_one("SELECT COUNT(*) AS c FROM enrolments WHERE status = 'dropped'")["c"]
    completion_rate = round((completed_count / enrol_count * 100.0), 1) if enrol_count > 0 else 0.0

    cert_count = query_one("SELECT COUNT(*) AS c FROM certificates")["c"]
    dropout_count = query_one("SELECT COUNT(*) AS c FROM vw_dropout_report")["c"]

    kpis = {
        "total_users": user_count,
        "total_courses": course_count,
        "total_enrolments": enrol_count,
        "completion_rate": completion_rate,
        "total_certificates": cert_count,
        "total_dropouts": dropout_count,
        "completed_count": completed_count,
        "active_count": active_count,
        "dropped_count": dropped_count
    }

    # Chart 1: Enrolments per Course
    courses_data = query_all("""
        SELECT c.title, COUNT(e.id) AS count
        FROM courses c
        LEFT JOIN enrolments e ON c.id = e.course_id
        GROUP BY c.id, c.title
        ORDER BY count DESC
        LIMIT 8
    """)
    chart_courses = {
        "labels": [c["title"][:22] + "..." if len(c["title"]) > 22 else c["title"] for c in courses_data],
        "counts": [c["count"] for c in courses_data]
    }

    # Chart 3: Enrolments Over Time (Monthly)
    timeline_data = query_all("""
        SELECT DATE_FORMAT(enrolled_at, '%b %Y') AS month_label, COUNT(*) AS count
        FROM enrolments
        GROUP BY DATE_FORMAT(enrolled_at, '%Y-%m'), DATE_FORMAT(enrolled_at, '%b %Y')
        ORDER BY MIN(enrolled_at) ASC
    """)
    chart_timeline = {
        "labels": [t["month_label"] for t in timeline_data],
        "counts": [t["count"] for t in timeline_data]
    }

    # Chart 4: Average Quiz Score per Course
    quiz_score_data = query_all("""
        SELECT c.title, ROUND(AVG(a.score), 1) AS avg_score
        FROM courses c
        JOIN modules m ON c.id = m.course_id
        JOIN quizzes q ON m.id = q.module_id
        JOIN attempts a ON q.id = a.quiz_id
        GROUP BY c.id, c.title
        ORDER BY avg_score DESC
        LIMIT 8
    """)
    chart_quizzes = {
        "labels": [q["title"][:20] + "..." if len(q["title"]) > 20 else q["title"] for q in quiz_score_data],
        "scores": [float(q["avg_score"] or 0) for q in quiz_score_data]
    }

    # Recent Enrolments
    recent_enrolments = query_all("""
        SELECT e.id, u.name AS learner_name, c.title AS course_title, e.status, e.progress, e.enrolled_at
        FROM enrolments e
        JOIN learners l ON e.learner_id = l.id
        JOIN users u ON l.user_id = u.id
        JOIN courses c ON e.course_id = c.id
        ORDER BY e.enrolled_at DESC
        LIMIT 6
    """)

    # Recent Certificates
    recent_certificates = query_all("""
        SELECT cert.id, cert.certificate_code, u.name AS learner_name, cert.issued_at
        FROM certificates cert
        JOIN enrolments e ON cert.enrolment_id = e.id
        JOIN learners l ON e.learner_id = l.id
        JOIN users u ON l.user_id = u.id
        ORDER BY cert.issued_at DESC
        LIMIT 5
    """)

    # Top Learners
    top_learners = query_all("""
        SELECT u.name, COUNT(e.id) AS completed_count
        FROM learners l
        JOIN users u ON l.user_id = u.id
        JOIN enrolments e ON l.id = e.learner_id AND e.status = 'completed'
        GROUP BY l.id, u.name
        ORDER BY completed_count DESC
        LIMIT 5
    """)

    return render_template(
        "admin/dashboard.html",
        active_page="admin_dashboard",
        kpis=kpis,
        chart_courses=chart_courses,
        chart_timeline=chart_timeline,
        chart_quizzes=chart_quizzes,
        recent_enrolments=recent_enrolments,
        recent_certificates=recent_certificates,
        top_learners=top_learners
    )


# -----------------------------------------------------------------------------
# 2. USERS MANAGEMENT (CRUD)
# -----------------------------------------------------------------------------
@admin_bp.route("/users")
@admin_required
def users():
    users_list = query_all("""
        SELECT u.id, u.name, u.email, u.role, u.created_at,
               i.title AS instructor_title, i.expertise, l.headline
        FROM users u
        LEFT JOIN instructors i ON u.id = i.user_id
        LEFT JOIN learners l ON u.id = l.user_id
        ORDER BY u.created_at DESC
    """)
    return render_template("admin/users.html", active_page="admin_users", users=users_list)


@admin_bp.route("/users/create", methods=["POST"])
@admin_required
def users_create():
    name = request.form.get("name", "").strip()
    email = request.form.get("email", "").strip()
    password = request.form.get("password", "").strip()
    role = request.form.get("role", "learner")
    headline = request.form.get("headline", "").strip()

    if not name or not email or not password:
        flash("All fields are required.", "error")
        return redirect(url_for("admin.users"))

    from routes.auth import hash_password
    pw_hash = hash_password(password)

    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("""
            INSERT INTO users (name, email, password_hash, role)
            VALUES (%s, %s, %s, %s)
        """, (name, email, pw_hash, role))
        user_id = cursor.lastrowid

        if role == "instructor":
            cursor.execute("""
                INSERT INTO instructors (user_id, title, expertise, bio)
                VALUES (%s, %s, %s, %s)
            """, (user_id, headline or "Course Instructor", headline or "Engineering", "Faculty profile"))
        elif role == "learner":
            cursor.execute("""
                INSERT INTO learners (user_id, headline)
                VALUES (%s, %s)
            """, (user_id, headline or "Student"))

        conn.commit()
        flash(f"User {name} created successfully.", "success")
    except Exception as e:
        conn.rollback()
        flash(f"Error creating user: {str(e)}", "error")
    finally:
        cursor.close()
        conn.close()

    return redirect(url_for("admin.users"))


@admin_bp.route("/users/edit/<int:user_id>", methods=["POST"])
@admin_required
def users_edit(user_id):
    name = request.form.get("name", "").strip()
    email = request.form.get("email", "").strip()
    role = request.form.get("role", "learner")
    headline = request.form.get("headline", "").strip()

    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("""
            UPDATE users SET name = %s, email = %s, role = %s WHERE id = %s
        """, (name, email, role, user_id))

        if role == "instructor":
            cursor.execute("""
                INSERT INTO instructors (user_id, title, expertise)
                VALUES (%s, %s, %s)
                ON DUPLICATE KEY UPDATE title = %s
            """, (user_id, headline, headline, headline))
        elif role == "learner":
            cursor.execute("""
                INSERT INTO learners (user_id, headline)
                VALUES (%s, %s)
                ON DUPLICATE KEY UPDATE headline = %s
            """, (user_id, headline, headline))

        conn.commit()
        flash("User updated successfully.", "success")
    except Exception as e:
        conn.rollback()
        flash(f"Failed to update user: {str(e)}", "error")
    finally:
        cursor.close()
        conn.close()

    return redirect(url_for("admin.users"))


@admin_bp.route("/users/delete/<int:user_id>", methods=["POST"])
@admin_required
def users_delete(user_id):
    try:
        execute_stmt("DELETE FROM users WHERE id = %s", (user_id,))
        flash("User and associated records deleted.", "success")
    except Exception as e:
        flash(f"Could not delete user: {str(e)}", "error")
    return redirect(url_for("admin.users"))


# -----------------------------------------------------------------------------
# 3. COURSES MANAGEMENT & DETAIL SYLLABUS TREE
# -----------------------------------------------------------------------------
@admin_bp.route("/courses")
@admin_required
def courses():
    courses_list = query_all("""
        SELECT c.*, u.name AS instructor_name, COUNT(e.id) AS total_enrolments
        FROM courses c
        JOIN instructors i ON c.instructor_id = i.id
        JOIN users u ON i.user_id = u.id
        LEFT JOIN enrolments e ON c.id = e.course_id
        GROUP BY c.id, u.name
        ORDER BY c.created_at DESC
    """)
    instructors_list = query_all("""
        SELECT i.id, u.name, i.expertise
        FROM instructors i
        JOIN users u ON i.user_id = u.id
    """)
    return render_template("admin/courses.html", active_page="admin_courses", courses=courses_list, instructors=instructors_list)


@admin_bp.route("/courses/create", methods=["POST"])
@admin_required
def courses_create():
    title = request.form.get("title", "").strip()
    category = request.form.get("category", "").strip()
    instructor_id = request.form.get("instructor_id", "I01")
    difficulty = request.form.get("difficulty", "beginner")
    status = request.form.get("status", "draft")
    passing_score = int(request.form.get("passing_score", 70))
    description = request.form.get("description", "").strip()

    slug = re.sub(r"[^a-zA-Z0-9]+", "-", title.lower()).strip("-") + f"-{int(time.time()) % 10000}"

    try:
        execute_stmt("""
            INSERT INTO courses (title, slug, instructor_id, category, difficulty, status, passing_score, description)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """, (title, slug, instructor_id, category, difficulty, status, passing_score, description))
        flash("Course track created successfully.", "success")
    except Exception as e:
        flash(f"Error creating course: {str(e)}", "error")

    return redirect(url_for("admin.courses"))


@admin_bp.route("/courses/edit/<int:course_id>", methods=["POST"])
@admin_required
def courses_edit(course_id):
    title = request.form.get("title", "").strip()
    category = request.form.get("category", "").strip()
    difficulty = request.form.get("difficulty", "beginner")
    status = request.form.get("status", "draft")
    passing_score = int(request.form.get("passing_score", 70))
    description = request.form.get("description", "").strip()

    try:
        execute_stmt("""
            UPDATE courses 
            SET title = %s, category = %s, difficulty = %s, status = %s, passing_score = %s, description = %s
            WHERE id = %s
        """, (title, category, difficulty, status, passing_score, description, course_id))
        flash("Course track updated successfully.", "success")
    except Exception as e:
        flash(f"Error updating course: {str(e)}", "error")

    return redirect(url_for("admin.courses"))


@admin_bp.route("/courses/delete/<int:course_id>", methods=["POST"])
@admin_required
def courses_delete(course_id):
    try:
        execute_stmt("DELETE FROM courses WHERE id = %s", (course_id,))
        flash("Course track deleted.", "success")
    except Exception as e:
        flash(f"Failed to delete course: {str(e)}", "error")
    return redirect(url_for("admin.courses"))


@admin_bp.route("/courses/<int:course_id>")
@admin_required
def course_detail(course_id):
    course = query_one("""
        SELECT c.*, u.name AS instructor_name, COUNT(e.id) AS total_enrolments
        FROM courses c
        JOIN instructors i ON c.instructor_id = i.id
        JOIN users u ON i.user_id = u.id
        LEFT JOIN enrolments e ON c.id = e.course_id
        WHERE c.id = %s
        GROUP BY c.id, u.name
    """, (course_id,))

    if not course:
        flash("Course not found.", "error")
        return redirect(url_for("admin.courses"))

    # Load modules, lessons, and quizzes hierarchy
    modules = query_all("SELECT * FROM modules WHERE course_id = %s ORDER BY order_num ASC", (course_id,))
    total_lessons = 0

    for m in modules:
        m["lessons"] = query_all("SELECT * FROM lessons WHERE module_id = %s ORDER BY order_num ASC", (m["id"],))
        total_lessons += len(m["lessons"])
        m["quizzes"] = query_all("""
            SELECT q.*, COUNT(ques.id) AS question_count
            FROM quizzes q
            LEFT JOIN questions ques ON q.id = ques.quiz_id
            WHERE q.module_id = %s
            GROUP BY q.id
        """, (m["id"],))

    return render_template(
        "admin/course_detail.html",
        active_page="admin_courses",
        course=course,
        modules=modules,
        total_lessons=total_lessons
    )


# -----------------------------------------------------------------------------
# 4. MODULES & LESSONS CRUD
# -----------------------------------------------------------------------------
@admin_bp.route("/modules/create", methods=["POST"])
@admin_required
def modules_create():
    course_id = int(request.form.get("course_id"))
    title = request.form.get("title", "").strip()
    order_num = int(request.form.get("order_num", 1))
    description = request.form.get("description", "").strip()

    try:
        execute_stmt("""
            INSERT INTO modules (course_id, title, order_num, description)
            VALUES (%s, %s, %s, %s)
        """, (course_id, title, order_num, description))
        flash("Module added to course curriculum.", "success")
    except Exception as e:
        flash(f"Error adding module: {str(e)}", "error")

    return redirect(url_for("admin.course_detail", course_id=course_id))


@admin_bp.route("/modules/delete/<int:module_id>", methods=["POST"])
@admin_required
def modules_delete(module_id):
    mod = query_one("SELECT course_id FROM modules WHERE id = %s", (module_id,))
    course_id = mod["course_id"] if mod else 1
    try:
        execute_stmt("DELETE FROM modules WHERE id = %s", (module_id,))
        flash("Module deleted.", "success")
    except Exception as e:
        flash(f"Error: {str(e)}", "error")
    return redirect(url_for("admin.course_detail", course_id=course_id))


@admin_bp.route("/lessons/create", methods=["POST"])
@admin_required
def lessons_create():
    course_id = int(request.form.get("course_id"))
    module_id = int(request.form.get("module_id"))
    title = request.form.get("title", "").strip()
    content_type = request.form.get("content_type", "reading")
    duration = int(request.form.get("duration_minutes", 15))
    content = request.form.get("content", "").strip()

    next_order = query_one("SELECT COALESCE(MAX(order_num), 0) + 1 AS next_o FROM lessons WHERE module_id = %s", (module_id,))["next_o"]

    try:
        execute_stmt("""
            INSERT INTO lessons (module_id, title, content_type, duration_minutes, content, order_num)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (module_id, title, content_type, duration, content, next_order))
        flash("Lesson saved to module.", "success")
    except Exception as e:
        flash(f"Error saving lesson: {str(e)}", "error")

    return redirect(url_for("admin.course_detail", course_id=course_id))


@admin_bp.route("/lessons/delete/<int:lesson_id>", methods=["POST"])
@admin_required
def lessons_delete(lesson_id):
    les = query_one("SELECT m.course_id FROM lessons l JOIN modules m ON l.module_id = m.id WHERE l.id = %s", (lesson_id,))
    course_id = les["course_id"] if les else 1
    try:
        execute_stmt("DELETE FROM lessons WHERE id = %s", (lesson_id,))
        flash("Lesson removed.", "success")
    except Exception as e:
        flash(f"Error: {str(e)}", "error")
    return redirect(url_for("admin.course_detail", course_id=course_id))


# -----------------------------------------------------------------------------
# 5. QUIZZES & QUESTION BUILDER
# -----------------------------------------------------------------------------
@admin_bp.route("/quizzes")
@admin_required
def quizzes():
    quiz_id = request.args.get("quiz_id", type=int)
    
    quizzes_list = query_all("""
        SELECT q.*, c.title AS course_title, m.title AS module_title
        FROM quizzes q
        JOIN modules m ON q.module_id = m.id
        JOIN courses c ON m.course_id = c.id
        ORDER BY q.created_at DESC
    """)

    for q in quizzes_list:
        q["questions"] = query_all("SELECT * FROM questions WHERE quiz_id = %s ORDER BY order_num ASC", (q["id"],))

    selected_quiz = None
    if quiz_id:
        selected_quiz = next((q for q in quizzes_list if q["id"] == quiz_id), None)
    if not selected_quiz and quizzes_list:
        selected_quiz = quizzes_list[0]

    return render_template(
        "admin/quizzes.html",
        active_page="admin_quizzes",
        quizzes=quizzes_list,
        selected_quiz=selected_quiz
    )


@admin_bp.route("/quizzes/create", methods=["POST"])
@admin_required
def quizzes_create():
    course_id = int(request.form.get("course_id"))
    module_id = int(request.form.get("module_id"))
    title = request.form.get("title", "").strip()
    total_marks = int(request.form.get("total_marks", 100))
    passing_marks = int(request.form.get("passing_marks", 70))
    max_attempts = int(request.form.get("max_attempts", 3))
    time_limit = int(request.form.get("time_limit_mins", 25))

    try:
        execute_stmt("""
            INSERT INTO quizzes (module_id, title, total_marks, passing_marks, max_attempts, time_limit_mins)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (module_id, title, total_marks, passing_marks, max_attempts, time_limit))
        flash("Quiz assessment created.", "success")
    except Exception as e:
        flash(f"Error: {str(e)}", "error")

    return redirect(url_for("admin.course_detail", course_id=course_id))


@admin_bp.route("/questions/create", methods=["POST"])
@admin_required
def questions_create():
    quiz_id = int(request.form.get("quiz_id"))
    q_text = request.form.get("question_text", "").strip()
    opt_a = request.form.get("option_a", "").strip()
    opt_b = request.form.get("option_b", "").strip()
    opt_c = request.form.get("option_c", "").strip()
    opt_d = request.form.get("option_d", "").strip()
    correct_opt = request.form.get("correct_option", "A")
    marks = int(request.form.get("marks", 20))

    next_order = query_one("SELECT COALESCE(MAX(order_num), 0) + 1 AS n FROM questions WHERE quiz_id = %s", (quiz_id,))["n"]

    try:
        execute_stmt("""
            INSERT INTO questions (quiz_id, question_text, option_a, option_b, option_c, option_d, correct_option, marks, order_num)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (quiz_id, q_text, opt_a, opt_b, opt_c, opt_d, correct_opt, marks, next_order))
        flash("Question added to quiz bank.", "success")
    except Exception as e:
        flash(f"Error adding question: {str(e)}", "error")

    return redirect(url_for("admin.quizzes", quiz_id=quiz_id))


@admin_bp.route("/questions/delete/<int:question_id>", methods=["POST"])
@admin_required
def questions_delete(question_id):
    quiz_id = request.args.get("quiz_id", type=int, default=1)
    try:
        execute_stmt("DELETE FROM questions WHERE id = %s", (question_id,))
        flash("Question removed from assessment.", "success")
    except Exception as e:
        flash(f"Error removing question: {str(e)}", "error")
    return redirect(url_for("admin.quizzes", quiz_id=quiz_id))


# -----------------------------------------------------------------------------
# 6. ENROLMENTS (CALLS STORED PROCEDURE enroll_learner)
# -----------------------------------------------------------------------------
@admin_bp.route("/enrolments")
@admin_required
def enrolments():
    enrolments_list = query_all("""
        SELECT e.id, u.name AS learner_name, u.email AS learner_email,
               c.title AS course_title, c.category, c.difficulty,
               e.status, e.progress, e.enrolled_at, e.completed_at
        FROM enrolments e
        JOIN learners l ON e.learner_id = l.id
        JOIN users u ON l.user_id = u.id
        JOIN courses c ON e.course_id = c.id
        ORDER BY e.enrolled_at DESC
    """)
    learners_list = query_all("SELECT l.id, u.name, u.email FROM learners l JOIN users u ON l.user_id = u.id ORDER BY u.name ASC")
    courses_list = query_all("SELECT id, title FROM courses WHERE status = 'published' ORDER BY title ASC")

    return render_template(
        "admin/enrolments.html",
        active_page="admin_enrolments",
        enrolments=enrolments_list,
        learners=learners_list,
        courses=courses_list
    )


@admin_bp.route("/enrolments/create", methods=["POST"])
@admin_required
def enrolments_create():
    learner_id = request.form.get("learner_id", "").strip()
    course_id = int(request.form.get("course_id"))

    # CALL enroll_learner STORED PROCEDURE!
    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("CALL enroll_learner(%s, %s, @enr_id, @status_code, @msg)", (learner_id, course_id))
        cursor.execute("SELECT @enr_id AS enr_id, @status_code AS status_code, @msg AS msg")
        res = cursor.fetchone()
        conn.commit()

        if res["status_code"] == "SUCCESS":
            flash(f"Successfully enrolled student! (Enrolment ID: {res['enr_id']})", "success")
        elif res["status_code"] == "ALREADY_ENROLLED":
            flash("Enrollment rejected: Student is already registered in this course.", "error")
        else:
            flash(f"Enrollment failed: {res['msg']}", "error")
    except Exception as e:
        conn.rollback()
        flash(f"Database error during enrollment: {str(e)}", "error")
    finally:
        cursor.close()
        conn.close()

    return redirect(url_for("admin.enrolments"))


@admin_bp.route("/enrolments/status/<int:enrolment_id>", methods=["POST"])
@admin_required
def enrolments_status(enrolment_id):
    status = request.form.get("status", "active")
    try:
        if status == "completed":
            execute_stmt("UPDATE enrolments SET status = 'completed', progress = 100.00, completed_at = NOW() WHERE id = %s", (enrolment_id,))
        elif status == "dropped":
            execute_stmt("UPDATE enrolments SET status = 'dropped', dropped_at = NOW() WHERE id = %s", (enrolment_id,))
        else:
            execute_stmt("UPDATE enrolments SET status = 'active' WHERE id = %s", (enrolment_id,))
        flash("Enrollment status updated.", "success")
    except Exception as e:
        flash(f"Failed to update status: {str(e)}", "error")
    return redirect(url_for("admin.enrolments"))


@admin_bp.route("/enrolments/delete/<int:enrolment_id>", methods=["POST"])
@admin_required
def enrolments_delete(enrolment_id):
    try:
        execute_stmt("DELETE FROM enrolments WHERE id = %s", (enrolment_id,))
        flash("Enrolment removed.", "success")
    except Exception as e:
        flash(f"Error: {str(e)}", "error")
    return redirect(url_for("admin.enrolments"))


# -----------------------------------------------------------------------------
# 7. ATTEMPTS & SCORES AUDIT
# -----------------------------------------------------------------------------
@admin_bp.route("/attempts")
@admin_required
def attempts():
    attempts_list = query_all("""
        SELECT a.*, q.title AS quiz_title, q.max_attempts, c.title AS course_title,
               u.name AS learner_name, u.email AS learner_email
        FROM attempts a
        JOIN quizzes q ON a.quiz_id = q.id
        JOIN modules m ON q.module_id = m.id
        JOIN courses c ON m.course_id = c.id
        JOIN learners l ON a.learner_id = l.id
        JOIN users u ON l.user_id = u.id
        ORDER BY a.started_at DESC
    """)

    for a in attempts_list:
        a["responses"] = query_all("""
            SELECT r.*, q.question_text, q.correct_option
            FROM responses r
            JOIN questions q ON r.question_id = q.id
            WHERE r.attempt_id = %s
            ORDER BY q.order_num ASC
        """, (a["id"],))

    quizzes_filter = query_all("SELECT id, title FROM quizzes ORDER BY title ASC")

    return render_template(
        "admin/attempts.html",
        active_page="admin_attempts",
        attempts=attempts_list,
        quizzes=quizzes_filter
    )


# -----------------------------------------------------------------------------
# 8. CERTIFICATES & ELIGIBILITY QUEUE
# -----------------------------------------------------------------------------
@admin_bp.route("/certificates")
@admin_required
def certificates():
    issued_list = query_all("""
        SELECT cert.*, u.name AS learner_name, u.email AS learner_email, c.title AS course_title
        FROM certificates cert
        JOIN enrolments e ON cert.enrolment_id = e.id
        JOIN learners l ON e.learner_id = l.id
        JOIN users u ON l.user_id = u.id
        JOIN courses c ON e.course_id = c.id
        ORDER BY cert.issued_at DESC
    """)

    # Query eligibility queue using view
    eligible_list = query_all("SELECT * FROM vw_certificate_eligibility WHERE is_eligible_to_issue = 1")

    return render_template(
        "admin/certificates.html",
        active_page="admin_certificates",
        certificates=issued_list,
        eligible_list=eligible_list
    )


@admin_bp.route("/certificates/issue/<int:enrolment_id>", methods=["POST"])
@admin_required
def certificates_issue(enrolment_id):
    # CALL issue_certificate STORED PROCEDURE!
    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("CALL issue_certificate(%s, @code, @status_code, @msg)", (enrolment_id,))
        cursor.execute("SELECT @code AS code, @status_code AS status_code, @msg AS msg")
        res = cursor.fetchone()
        conn.commit()

        if res["status_code"] == "SUCCESS":
            flash(f"Certificate issued successfully! Verification code: {res['code']}", "success")
        elif res["status_code"] == "ALREADY_ISSUED":
            flash(f"Certificate already issued. Code: {res['code']}", "info")
        else:
            flash(f"Certification rejected: {res['msg']}", "error")
    except Exception as e:
        conn.rollback()
        flash(f"Database error during certificate issuance: {str(e)}", "error")
    finally:
        cursor.close()
        conn.close()

    return redirect(url_for("admin.certificates"))


# -----------------------------------------------------------------------------
# 9. STUDENT FEEDBACK & REVIEWS
# -----------------------------------------------------------------------------
@admin_bp.route("/feedback")
@admin_required
def feedback():
    feedback_list = query_all("""
        SELECT f.*, u.name AS learner_name, l.headline, c.id AS course_id, c.title AS course_title
        FROM feedback f
        JOIN enrolments e ON f.enrolment_id = e.id
        JOIN learners l ON e.learner_id = l.id
        JOIN users u ON l.user_id = u.id
        JOIN courses c ON e.course_id = c.id
        ORDER BY f.created_at DESC
    """)
    courses_filter = query_all("SELECT id, title FROM courses ORDER BY title ASC")

    avg_rating = round(query_one("SELECT AVG(rating) AS a FROM feedback")["a"] or 5.0, 1)
    five_star_count = query_one("SELECT COUNT(*) AS c FROM feedback WHERE rating = 5")["c"]
    four_star_count = query_one("SELECT COUNT(*) AS c FROM feedback WHERE rating = 4")["c"]

    return render_template(
        "admin/feedback.html",
        active_page="admin_feedback",
        feedback_list=feedback_list,
        courses=courses_filter,
        avg_rating=avg_rating,
        five_star_count=five_star_count,
        four_star_count=four_star_count
    )


# -----------------------------------------------------------------------------
# 10. SYSTEM REPORTS (6 VIEWS + CSV EXPORT)
# -----------------------------------------------------------------------------
@admin_bp.route("/reports")
@admin_required
def reports():
    tab = request.args.get("tab", "course_completion")

    data_course_completion = query_all("SELECT * FROM vw_course_completion")
    data_learner_progress = query_all("SELECT * FROM vw_learner_progress LIMIT 50")
    data_dropout_report = query_all("SELECT * FROM vw_dropout_report")
    data_quiz_performance = query_all("SELECT * FROM vw_quiz_performance")
    data_certificate_eligibility = query_all("SELECT * FROM vw_certificate_eligibility")
    data_instructor_summary = query_all("SELECT * FROM vw_instructor_summary")

    # Chart data for course completion
    chart_completion = {
        "labels": [c["course_title"][:20] + "..." for c in data_course_completion],
        "rates": [float(c["completion_rate_pct"] or 0) for c in data_course_completion]
    }

    return render_template(
        "admin/reports.html",
        active_page="admin_reports",
        selected_tab=tab,
        data_course_completion=data_course_completion,
        data_learner_progress=data_learner_progress,
        data_dropout_report=data_dropout_report,
        data_quiz_performance=data_quiz_performance,
        data_certificate_eligibility=data_certificate_eligibility,
        data_instructor_summary=data_instructor_summary,
        chart_completion=chart_completion
    )


@admin_bp.route("/reports/export")
@admin_required
def reports_export():
    view_name = request.args.get("view", "course_completion")
    view_map = {
        "course_completion": "vw_course_completion",
        "learner_progress": "vw_learner_progress",
        "dropout_report": "vw_dropout_report",
        "quiz_performance": "vw_quiz_performance",
        "cert_eligibility": "vw_certificate_eligibility",
        "instructor_summary": "vw_instructor_summary"
    }
    actual_view = view_map.get(view_name, "vw_course_completion")

    rows = query_all(f"SELECT * FROM `{actual_view}`")
    if not rows:
        return "No data to export", 400

    si = io.StringIO()
    cw = csv.DictWriter(si, fieldnames=list(rows[0].keys()))
    cw.writeheader()
    cw.writerows(rows)

    output = io.BytesIO(si.getvalue().encode("utf-8"))
    filename = f"{actual_view}_export_{int(time.time())}.csv"
    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment;filename={filename}"}
    )


# -----------------------------------------------------------------------------
# 11. SQL CONSOLE (ADMIN ONLY, READ-ONLY GUARDED)
# -----------------------------------------------------------------------------
@admin_bp.route("/sql-console", methods=["GET", "POST"])
@admin_required
def sql_console():
    query_text = "SELECT * FROM vw_course_completion LIMIT 10;"
    rows = []
    columns = []
    execution_time = None
    error_msg = None

    if request.method == "POST":
        query_text = request.form.get("sql_query", "").strip()

        # Security check: MUST start with SELECT and cannot contain mutation keywords
        clean_query = query_text.strip().rstrip(";")
        first_word = clean_query.split()[0].upper() if clean_query else ""
        dangerous_patterns = [r"\bDROP\b", r"\bDELETE\b", r"\bUPDATE\b", r"\bINSERT\b", r"\bALTER\b", r"\bTRUNCATE\b", r"\bGRANT\b", r"\bREVOKE\b"]

        if first_word != "SELECT":
            error_msg = "Security Policy Violation: SQL Console is strictly read-only. Only SELECT queries are permitted."
        elif any(re.search(pat, clean_query, re.IGNORECASE) for pat in dangerous_patterns):
            error_msg = "Security Policy Violation: Query contains prohibited modification statements."
        else:
            conn = get_db()
            cursor = conn.cursor(dictionary=True)
            try:
                start_time = time.perf_counter()
                cursor.execute(clean_query)
                rows = cursor.fetchall()
                execution_time = round((time.perf_counter() - start_time) * 1000, 2)
                if rows:
                    columns = list(rows[0].keys())
                else:
                    columns = [d[0] for d in cursor.description] if cursor.description else []
            except Exception as e:
                error_msg = str(e)
            finally:
                cursor.close()
                conn.close()

    return render_template(
        "admin/sql_console.html",
        active_page="admin_sql",
        query_text=query_text,
        rows=rows,
        columns=columns,
        execution_time=execution_time,
        error_msg=error_msg
    )


# -----------------------------------------------------------------------------
# 11. REUSABLE TABLE BROWSER (CRUD & SCHEMA FOR ALL 14 TABLES)
# -----------------------------------------------------------------------------
@admin_bp.route("/tables/<table_name>")
@admin_required
def table_browser(table_name):
    if table_name not in ALL_TABLES:
        flash(f"Table '{table_name}' does not exist.", "error")
        return redirect(url_for("admin.dashboard"))

    page = request.args.get("page", 1, type=int)
    per_page_arg = request.args.get("per_page", "all")
    if per_page_arg in ("all", "ALL", "0", ""):
        per_page = 1000
    else:
        try:
            per_page = max(1, int(per_page_arg))
        except (ValueError, TypeError):
            per_page = 1000

    search = request.args.get("q", "").strip()
    sort_col = request.args.get("sort", "").strip()
    sort_dir = request.args.get("dir", "asc").strip()
    active_tab = request.args.get("tab", "data")

    schema = get_table_schema(table_name)
    fk_options = get_fk_options_for_table(table_name)
    rows, total_rows, total_pages, columns = get_table_data(
        table_name,
        page=page,
        per_page=per_page,
        search=search,
        sort_col=sort_col,
        sort_dir=sort_dir
    )

    return render_template(
        "admin/table_browser.html",
        table_name=table_name,
        schema=schema,
        fk_options=fk_options,
        rows=rows,
        total_rows=total_rows,
        total_pages=total_pages,
        page=page,
        per_page=per_page,
        per_page_arg=per_page_arg,
        search=search,
        sort_col=sort_col or schema["primary_key"],
        sort_dir=sort_dir,
        active_tab=active_tab,
        active_page=f"table_{table_name}"
    )


@admin_bp.route("/tables/<table_name>/create", methods=["POST"])
@admin_required
def table_create(table_name):
    if table_name not in ALL_TABLES:
        flash(f"Table '{table_name}' does not exist.", "error")
        return redirect(url_for("admin.dashboard"))

    ok, msg, new_id = insert_row(table_name, request.form.to_dict())
    if ok:
        flash(f"{table_name.capitalize()} record #{new_id} created successfully.", "success")
    else:
        flash(msg, "error")

    return redirect(url_for("admin.table_browser", table_name=table_name))


@admin_bp.route("/tables/<table_name>/update/<int:record_id>", methods=["POST"])
@admin_required
def table_update(table_name, record_id):
    if table_name not in ALL_TABLES:
        flash(f"Table '{table_name}' does not exist.", "error")
        return redirect(url_for("admin.dashboard"))

    ok, msg = update_row(table_name, record_id, request.form.to_dict())
    if ok:
        flash(f"{table_name.capitalize()} record #{record_id} updated successfully.", "success")
    else:
        flash(msg, "error")

    return redirect(url_for("admin.table_browser", table_name=table_name))


@admin_bp.route("/tables/<table_name>/delete/<int:record_id>", methods=["POST"])
@admin_required
def table_delete(table_name, record_id):
    if table_name not in ALL_TABLES:
        flash(f"Table '{table_name}' does not exist.", "error")
        return redirect(url_for("admin.dashboard"))

    ok, msg = delete_row(table_name, record_id)
    if ok:
        flash(f"{table_name.capitalize()} record #{record_id} deleted successfully.", "success")
    else:
        flash(msg, "error")

    return redirect(url_for("admin.table_browser", table_name=table_name))


# -----------------------------------------------------------------------------
# 12. VIEWS BROWSER (READ-ONLY FOR ALL 6 VIEWS)
# -----------------------------------------------------------------------------
@admin_bp.route("/views/<view_name>")
@admin_required
def view_browser(view_name):
    if view_name not in ALL_VIEWS:
        flash(f"View '{view_name}' does not exist.", "error")
        return redirect(url_for("admin.reports"))

    page = request.args.get("page", 1, type=int)
    per_page_arg = request.args.get("per_page", "all")
    if per_page_arg in ("all", "ALL", "0", ""):
        per_page = 1000
    else:
        try:
            per_page = max(1, int(per_page_arg))
        except (ValueError, TypeError):
            per_page = 1000

    search = request.args.get("q", "").strip()
    sort_col = request.args.get("sort", "").strip()
    sort_dir = request.args.get("dir", "asc").strip()

    schema = get_table_schema(view_name)
    rows, total_rows, total_pages, columns = get_table_data(
        view_name,
        page=page,
        per_page=per_page,
        search=search,
        sort_col=sort_col,
        sort_dir=sort_dir
    )

    return render_template(
        "admin/view_browser.html",
        view_name=view_name,
        schema=schema,
        rows=rows,
        total_rows=total_rows,
        total_pages=total_pages,
        page=page,
        per_page=per_page,
        per_page_arg=per_page_arg,
        search=search,
        sort_col=sort_col or (schema["columns"][0]["name"] if schema["columns"] else ""),
        sort_dir=sort_dir,
        active_page=f"view_{view_name}"
    )


@admin_bp.route("/views/<view_name>/export")
@admin_required
def view_export_csv(view_name):
    if view_name not in ALL_VIEWS:
        return "Invalid view", 400

    rows = query_all(f"SELECT * FROM `{view_name}`")
    if not rows:
        return "No data", 200

    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=list(rows[0].keys()))
    writer.writeheader()
    for r in rows:
        writer.writerow(r)

    output.seek(0)
    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment;filename={view_name}.csv"}
    )

