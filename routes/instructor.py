from functools import wraps
from flask import Blueprint, render_template, request, redirect, url_for, session, flash, jsonify
from db import query_all, query_one, get_db
from table_service import translate_db_error

instructor_bp = Blueprint("instructor", __name__, url_prefix="/instructor")


def instructor_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get("is_instructor") and not session.get("is_admin"):
            flash("Instructor mode required. Please unlock instructor mode.", "warning")
            return redirect(url_for("learner.dashboard"))
        return f(*args, **kwargs)
    return decorated_function


def get_current_instructor():
    """Retrieve the active instructor profile for the session."""
    inst_id = session.get("instructor_id")
    if inst_id:
        inst = query_one("SELECT i.*, u.name, u.email FROM instructors i JOIN users u ON i.user_id = u.id WHERE i.id = %s", (inst_id,))
        if inst:
            return inst
    
    # Fallback to Arthur Morgan
    inst = query_one("SELECT i.*, u.name, u.email FROM instructors i JOIN users u ON i.user_id = u.id WHERE i.id = 'I02'")
    return inst


# -----------------------------------------------------------------------------
# 1. INSTRUCTOR STUDIO DASHBOARD
# -----------------------------------------------------------------------------
@instructor_bp.route("/dashboard")
@instructor_required
def dashboard():
    inst = get_current_instructor()
    instructor_id = inst["id"]

    my_courses = query_all("""
        SELECT c.*, 
               COUNT(DISTINCT e.id) AS enrolments_count,
               COUNT(DISTINCT CASE WHEN e.status = 'completed' THEN e.id END) AS completions_count
        FROM courses c
        LEFT JOIN enrolments e ON c.id = e.course_id
        WHERE c.instructor_id = %s
        GROUP BY c.id
        ORDER BY c.created_at DESC
    """, (instructor_id,))

    stats = query_one("""
        SELECT total_students_enrolled, total_completions, avg_course_rating, total_reviews_received
        FROM vw_instructor_summary
        WHERE instructor_id = %s
    """, (instructor_id,)) or {
        "total_students_enrolled": 0,
        "total_completions": 0,
        "avg_course_rating": 5.0,
        "total_reviews_received": 0
    }

    # Module and quiz counts for this instructor
    modules_count = query_one("""
        SELECT COUNT(m.id) AS count
        FROM modules m
        JOIN courses c ON m.course_id = c.id
        WHERE c.instructor_id = %s
    """, (instructor_id,))["count"]

    lessons_count = query_one("""
        SELECT COUNT(l.id) AS count
        FROM lessons l
        JOIN modules m ON l.module_id = m.id
        JOIN courses c ON m.course_id = c.id
        WHERE c.instructor_id = %s
    """, (instructor_id,))["count"]

    quizzes_count = query_one("""
        SELECT COUNT(q.id) AS count
        FROM quizzes q
        JOIN modules m ON q.module_id = m.id
        JOIN courses c ON m.course_id = c.id
        WHERE c.instructor_id = %s
    """, (instructor_id,))["count"]

    return render_template(
        "instructor/dashboard.html",
        active_page="inst_dashboard",
        instructor=inst,
        my_courses=my_courses,
        total_students=stats.get("total_students_enrolled") or 0,
        total_completions=stats.get("total_completions") or 0,
        avg_rating=stats.get("avg_course_rating") or 5.0,
        total_reviews=stats.get("total_reviews_received") or 0,
        modules_count=modules_count,
        lessons_count=lessons_count,
        quizzes_count=quizzes_count
    )


# -----------------------------------------------------------------------------
# 2. MY COURSES (Only courses taught by this instructor)
# -----------------------------------------------------------------------------
@instructor_bp.route("/courses")
@instructor_required
def courses():
    inst = get_current_instructor()
    courses_list = query_all("""
        SELECT c.*,
               COUNT(DISTINCT m.id) AS modules_count,
               COUNT(DISTINCT e.id) AS enrolments_count
        FROM courses c
        LEFT JOIN modules m ON c.id = m.course_id
        LEFT JOIN enrolments e ON c.id = e.course_id
        WHERE c.instructor_id = %s
        GROUP BY c.id
        ORDER BY c.created_at DESC
    """, (inst["id"],))

    return render_template(
        "instructor/courses.html",
        active_page="inst_courses",
        instructor=inst,
        courses=courses_list
    )


@instructor_bp.route("/courses/create", methods=["POST"])
@instructor_required
def courses_create():
    inst = get_current_instructor()
    title = request.form.get("title", "").strip()
    slug = request.form.get("slug", "").strip() or title.lower().replace(" ", "-")[:50]
    description = request.form.get("description", "").strip()
    category = request.form.get("category", "Computer Science").strip()
    difficulty = request.form.get("difficulty", "intermediate")
    status = request.form.get("status", "published")

    if not title:
        flash("Course title is required.", "error")
        return redirect(url_for("instructor.courses"))

    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("""
            INSERT INTO courses (title, slug, description, category, difficulty, status, instructor_id)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, (title, slug, description, category, difficulty, status, inst["id"]))
        conn.commit()
        flash(f"Course '{title}' created successfully under your profile.", "success")
    except Exception as e:
        conn.rollback()
        flash(translate_db_error(e), "error")
    finally:
        cursor.close()
        conn.close()

    return redirect(url_for("instructor.courses"))


@instructor_bp.route("/courses/edit/<int:course_id>", methods=["POST"])
@instructor_required
def courses_edit(course_id):
    inst = get_current_instructor()
    # Validate ownership
    c = query_one("SELECT * FROM courses WHERE id = %s AND instructor_id = %s", (course_id, inst["id"]))
    if not c:
        flash("Permission denied: You can only edit your own courses.", "error")
        return redirect(url_for("instructor.courses"))

    title = request.form.get("title", "").strip()
    description = request.form.get("description", "").strip()
    category = request.form.get("category", c["category"]).strip()
    difficulty = request.form.get("difficulty", c["difficulty"])
    status = request.form.get("status", c["status"])

    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("""
            UPDATE courses 
            SET title = %s, description = %s, category = %s, difficulty = %s, status = %s
            WHERE id = %s AND instructor_id = %s
        """, (title, description, category, difficulty, status, course_id, inst["id"]))
        conn.commit()
        flash(f"Course '{title}' updated successfully.", "success")
    except Exception as e:
        conn.rollback()
        flash(translate_db_error(e), "error")
    finally:
        cursor.close()
        conn.close()

    return redirect(url_for("instructor.courses"))


# -----------------------------------------------------------------------------
# 3. MODULES (Strictly for this instructor's courses)
# -----------------------------------------------------------------------------
@instructor_bp.route("/modules")
@instructor_required
def modules():
    inst = get_current_instructor()
    my_courses = query_all("SELECT id, title FROM courses WHERE instructor_id = %s ORDER BY title ASC", (inst["id"],))

    modules_list = query_all("""
        SELECT m.*, c.title AS course_title,
               COUNT(DISTINCT l.id) AS lessons_count,
               COUNT(DISTINCT q.id) AS quizzes_count
        FROM modules m
        JOIN courses c ON m.course_id = c.id
        LEFT JOIN lessons l ON m.id = l.module_id
        LEFT JOIN quizzes q ON m.id = q.module_id
        WHERE c.instructor_id = %s
        GROUP BY m.id
        ORDER BY c.title ASC, m.order_num ASC
    """, (inst["id"],))

    return render_template(
        "instructor/modules.html",
        active_page="inst_modules",
        instructor=inst,
        modules=modules_list,
        my_courses=my_courses
    )


@instructor_bp.route("/modules/create", methods=["POST"])
@instructor_required
def modules_create():
    inst = get_current_instructor()
    course_id = request.form.get("course_id")
    title = request.form.get("title", "").strip()
    order_num = request.form.get("order_num", 1, type=int)

    # Validate that course belongs to this instructor
    course = query_one("SELECT * FROM courses WHERE id = %s AND instructor_id = %s", (course_id, inst["id"]))
    if not course:
        flash("Permission denied: You can only add modules to your own courses.", "error")
        return redirect(url_for("instructor.modules"))

    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("""
            INSERT INTO modules (course_id, title, order_num)
            VALUES (%s, %s, %s)
        """, (course_id, title, order_num))
        conn.commit()
        flash(f"Module '{title}' added to '{course['title']}'.", "success")
    except Exception as e:
        conn.rollback()
        flash(translate_db_error(e), "error")
    finally:
        cursor.close()
        conn.close()

    return redirect(url_for("instructor.modules"))


@instructor_bp.route("/modules/edit/<int:module_id>", methods=["POST"])
@instructor_required
def modules_edit(module_id):
    inst = get_current_instructor()
    mod = query_one("""
        SELECT m.* FROM modules m
        JOIN courses c ON m.course_id = c.id
        WHERE m.id = %s AND c.instructor_id = %s
    """, (module_id, inst["id"]))

    if not mod:
        flash("Permission denied: You can only edit modules in your own courses.", "error")
        return redirect(url_for("instructor.modules"))

    title = request.form.get("title", "").strip()
    order_num = request.form.get("order_num", mod["order_num"], type=int)

    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("UPDATE modules SET title = %s, order_num = %s WHERE id = %s", (title, order_num, module_id))
        conn.commit()
        flash(f"Module #{module_id} updated successfully.", "success")
    except Exception as e:
        conn.rollback()
        flash(translate_db_error(e), "error")
    finally:
        cursor.close()
        conn.close()

    return redirect(url_for("instructor.modules"))


@instructor_bp.route("/modules/delete/<int:module_id>", methods=["POST"])
@instructor_required
def modules_delete(module_id):
    inst = get_current_instructor()
    mod = query_one("""
        SELECT m.* FROM modules m
        JOIN courses c ON m.course_id = c.id
        WHERE m.id = %s AND c.instructor_id = %s
    """, (module_id, inst["id"]))

    if not mod:
        flash("Permission denied: You can only delete modules in your own courses.", "error")
        return redirect(url_for("instructor.modules"))

    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("DELETE FROM modules WHERE id = %s", (module_id,))
        conn.commit()
        flash(f"Module #{module_id} deleted successfully.", "success")
    except Exception as e:
        conn.rollback()
        flash(translate_db_error(e), "error")
    finally:
        cursor.close()
        conn.close()

    return redirect(url_for("instructor.modules"))


# -----------------------------------------------------------------------------
# 4. LESSONS (Strictly for this instructor's modules/courses)
# -----------------------------------------------------------------------------
@instructor_bp.route("/lessons")
@instructor_required
def lessons():
    inst = get_current_instructor()
    my_modules = query_all("""
        SELECT m.id, m.title, c.title AS course_title
        FROM modules m
        JOIN courses c ON m.course_id = c.id
        WHERE c.instructor_id = %s
        ORDER BY c.title ASC, m.order_num ASC
    """, (inst["id"],))

    lessons_list = query_all("""
        SELECT l.*, m.title AS module_title, c.title AS course_title
        FROM lessons l
        JOIN modules m ON l.module_id = m.id
        JOIN courses c ON m.course_id = c.id
        WHERE c.instructor_id = %s
        ORDER BY c.title ASC, m.order_num ASC, l.order_num ASC
    """, (inst["id"],))

    return render_template(
        "instructor/lessons.html",
        active_page="inst_lessons",
        instructor=inst,
        lessons=lessons_list,
        my_modules=my_modules
    )


@instructor_bp.route("/lessons/create", methods=["POST"])
@instructor_required
def lessons_create():
    inst = get_current_instructor()
    module_id = request.form.get("module_id")
    title = request.form.get("title", "").strip()
    content = request.form.get("content", "").strip()
    duration_minutes = request.form.get("duration_minutes", 15, type=int)
    order_num = request.form.get("order_num", 1, type=int)

    # Validate module ownership
    mod = query_one("""
        SELECT m.* FROM modules m
        JOIN courses c ON m.course_id = c.id
        WHERE m.id = %s AND c.instructor_id = %s
    """, (module_id, inst["id"]))
    if not mod:
        flash("Permission denied: You can only add lessons to your own modules.", "error")
        return redirect(url_for("instructor.lessons"))

    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("""
            INSERT INTO lessons (module_id, title, content, duration_minutes, order_num)
            VALUES (%s, %s, %s, %s, %s)
        """, (module_id, title, content, duration_minutes, order_num))
        conn.commit()
        flash(f"Lesson '{title}' added to '{mod['title']}'.", "success")
    except Exception as e:
        conn.rollback()
        flash(translate_db_error(e), "error")
    finally:
        cursor.close()
        conn.close()

    return redirect(url_for("instructor.lessons"))


@instructor_bp.route("/lessons/edit/<int:lesson_id>", methods=["POST"])
@instructor_required
def lessons_edit(lesson_id):
    inst = get_current_instructor()
    les = query_one("""
        SELECT l.* FROM lessons l
        JOIN modules m ON l.module_id = m.id
        JOIN courses c ON m.course_id = c.id
        WHERE l.id = %s AND c.instructor_id = %s
    """, (lesson_id, inst["id"]))
    if not les:
        flash("Permission denied: You can only edit lessons in your own courses.", "error")
        return redirect(url_for("instructor.lessons"))

    title = request.form.get("title", "").strip()
    content = request.form.get("content", "").strip()
    duration_minutes = request.form.get("duration_minutes", les["duration_minutes"], type=int)
    order_num = request.form.get("order_num", les["order_num"], type=int)

    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("""
            UPDATE lessons
            SET title = %s, content = %s, duration_minutes = %s, order_num = %s
            WHERE id = %s
        """, (title, content, duration_minutes, order_num, lesson_id))
        conn.commit()
        flash(f"Lesson #{lesson_id} updated successfully.", "success")
    except Exception as e:
        conn.rollback()
        flash(translate_db_error(e), "error")
    finally:
        cursor.close()
        conn.close()

    return redirect(url_for("instructor.lessons"))


@instructor_bp.route("/lessons/delete/<int:lesson_id>", methods=["POST"])
@instructor_required
def lessons_delete(lesson_id):
    inst = get_current_instructor()
    les = query_one("""
        SELECT l.* FROM lessons l
        JOIN modules m ON l.module_id = m.id
        JOIN courses c ON m.course_id = c.id
        WHERE l.id = %s AND c.instructor_id = %s
    """, (lesson_id, inst["id"]))
    if not les:
        flash("Permission denied: You can only delete lessons in your own courses.", "error")
        return redirect(url_for("instructor.lessons"))

    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("DELETE FROM lessons WHERE id = %s", (lesson_id,))
        conn.commit()
        flash(f"Lesson #{lesson_id} deleted successfully.", "success")
    except Exception as e:
        conn.rollback()
        flash(translate_db_error(e), "error")
    finally:
        cursor.close()
        conn.close()

    return redirect(url_for("instructor.lessons"))


# -----------------------------------------------------------------------------
# 5. QUIZZES (Strictly for this instructor's modules/courses)
# -----------------------------------------------------------------------------
@instructor_bp.route("/quizzes")
@instructor_required
def quizzes():
    inst = get_current_instructor()
    my_modules = query_all("""
        SELECT m.id, m.title, c.title AS course_title
        FROM modules m
        JOIN courses c ON m.course_id = c.id
        WHERE c.instructor_id = %s
        ORDER BY c.title ASC, m.order_num ASC
    """, (inst["id"],))

    quizzes_list = query_all("""
        SELECT q.*, m.title AS module_title, c.title AS course_title,
               COUNT(DISTINCT qs.id) AS questions_count
        FROM quizzes q
        JOIN modules m ON q.module_id = m.id
        JOIN courses c ON m.course_id = c.id
        LEFT JOIN questions qs ON q.id = qs.quiz_id
        WHERE c.instructor_id = %s
        GROUP BY q.id
        ORDER BY c.title ASC, m.order_num ASC
    """, (inst["id"],))

    return render_template(
        "instructor/quizzes.html",
        active_page="inst_quizzes",
        instructor=inst,
        quizzes=quizzes_list,
        my_modules=my_modules
    )


@instructor_bp.route("/quizzes/create", methods=["POST"])
@instructor_required
def quizzes_create():
    inst = get_current_instructor()
    module_id = request.form.get("module_id")
    title = request.form.get("title", "").strip()
    pass_marks = request.form.get("pass_marks", 70, type=int)
    max_attempts = request.form.get("max_attempts", 3, type=int)

    # Validate module ownership
    mod = query_one("""
        SELECT m.* FROM modules m
        JOIN courses c ON m.course_id = c.id
        WHERE m.id = %s AND c.instructor_id = %s
    """, (module_id, inst["id"]))
    if not mod:
        flash("Permission denied: You can only add quizzes to your own modules.", "error")
        return redirect(url_for("instructor.quizzes"))

    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("""
            INSERT INTO quizzes (module_id, title, pass_marks, max_attempts)
            VALUES (%s, %s, %s, %s)
        """, (module_id, title, pass_marks, max_attempts))
        conn.commit()
        flash(f"Quiz '{title}' added to '{mod['title']}'.", "success")
    except Exception as e:
        conn.rollback()
        flash(translate_db_error(e), "error")
    finally:
        cursor.close()
        conn.close()

    return redirect(url_for("instructor.quizzes"))


@instructor_bp.route("/quizzes/edit/<int:quiz_id>", methods=["POST"])
@instructor_required
def quizzes_edit(quiz_id):
    inst = get_current_instructor()
    q = query_one("""
        SELECT q.* FROM quizzes q
        JOIN modules m ON q.module_id = m.id
        JOIN courses c ON m.course_id = c.id
        WHERE q.id = %s AND c.instructor_id = %s
    """, (quiz_id, inst["id"]))
    if not q:
        flash("Permission denied: You can only edit quizzes in your own courses.", "error")
        return redirect(url_for("instructor.quizzes"))

    title = request.form.get("title", "").strip()
    pass_marks = request.form.get("pass_marks", q["pass_marks"], type=int)
    max_attempts = request.form.get("max_attempts", q["max_attempts"], type=int)

    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("""
            UPDATE quizzes
            SET title = %s, pass_marks = %s, max_attempts = %s
            WHERE id = %s
        """, (title, pass_marks, max_attempts, quiz_id))
        conn.commit()
        flash(f"Quiz #{quiz_id} updated successfully.", "success")
    except Exception as e:
        conn.rollback()
        flash(translate_db_error(e), "error")
    finally:
        cursor.close()
        conn.close()

    return redirect(url_for("instructor.quizzes"))


@instructor_bp.route("/quizzes/delete/<int:quiz_id>", methods=["POST"])
@instructor_required
def quizzes_delete(quiz_id):
    inst = get_current_instructor()
    q = query_one("""
        SELECT q.* FROM quizzes q
        JOIN modules m ON q.module_id = m.id
        JOIN courses c ON m.course_id = c.id
        WHERE q.id = %s AND c.instructor_id = %s
    """, (quiz_id, inst["id"]))
    if not q:
        flash("Permission denied: You can only delete quizzes in your own courses.", "error")
        return redirect(url_for("instructor.quizzes"))

    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("DELETE FROM quizzes WHERE id = %s", (quiz_id,))
        conn.commit()
        flash(f"Quiz #{quiz_id} deleted successfully.", "success")
    except Exception as e:
        conn.rollback()
        flash(translate_db_error(e), "error")
    finally:
        cursor.close()
        conn.close()

    return redirect(url_for("instructor.quizzes"))


# -----------------------------------------------------------------------------
# 6. QUESTIONS (Strictly for this instructor's quizzes)
# -----------------------------------------------------------------------------
@instructor_bp.route("/questions")
@instructor_required
def questions():
    inst = get_current_instructor()
    my_quizzes = query_all("""
        SELECT q.id, q.title, c.title AS course_title
        FROM quizzes q
        JOIN modules m ON q.module_id = m.id
        JOIN courses c ON m.course_id = c.id
        WHERE c.instructor_id = %s
        ORDER BY c.title ASC, q.title ASC
    """, (inst["id"],))

    questions_list = query_all("""
        SELECT qs.*, q.title AS quiz_title, c.title AS course_title
        FROM questions qs
        JOIN quizzes q ON qs.quiz_id = q.id
        JOIN modules m ON q.module_id = m.id
        JOIN courses c ON m.course_id = c.id
        WHERE c.instructor_id = %s
        ORDER BY q.title ASC, qs.order_num ASC
    """, (inst["id"],))

    return render_template(
        "instructor/questions.html",
        active_page="inst_questions",
        instructor=inst,
        questions=questions_list,
        my_quizzes=my_quizzes
    )


@instructor_bp.route("/questions/create", methods=["POST"])
@instructor_required
def questions_create():
    inst = get_current_instructor()
    quiz_id = request.form.get("quiz_id")
    question_text = request.form.get("question_text", "").strip()
    option_a = request.form.get("option_a", "").strip()
    option_b = request.form.get("option_b", "").strip()
    option_c = request.form.get("option_c", "").strip()
    option_d = request.form.get("option_d", "").strip()
    correct_option = request.form.get("correct_option", "A").upper()
    marks = request.form.get("marks", 20, type=int)
    order_num = request.form.get("order_num", 1, type=int)

    # Validate quiz ownership
    q = query_one("""
        SELECT q.* FROM quizzes q
        JOIN modules m ON q.module_id = m.id
        JOIN courses c ON m.course_id = c.id
        WHERE q.id = %s AND c.instructor_id = %s
    """, (quiz_id, inst["id"]))
    if not q:
        flash("Permission denied: You can only add questions to your own quizzes.", "error")
        return redirect(url_for("instructor.questions"))

    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("""
            INSERT INTO questions (quiz_id, question_text, option_a, option_b, option_c, option_d, correct_option, marks, order_num)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (quiz_id, question_text, option_a, option_b, option_c, option_d, correct_option, marks, order_num))
        conn.commit()
        flash("Question added successfully.", "success")
    except Exception as e:
        conn.rollback()
        flash(translate_db_error(e), "error")
    finally:
        cursor.close()
        conn.close()

    return redirect(url_for("instructor.questions"))


@instructor_bp.route("/questions/edit/<int:question_id>", methods=["POST"])
@instructor_required
def questions_edit(question_id):
    inst = get_current_instructor()
    qs = query_one("""
        SELECT qs.* FROM questions qs
        JOIN quizzes q ON qs.quiz_id = q.id
        JOIN modules m ON q.module_id = m.id
        JOIN courses c ON m.course_id = c.id
        WHERE qs.id = %s AND c.instructor_id = %s
    """, (question_id, inst["id"]))
    if not qs:
        flash("Permission denied: You can only edit questions in your own quizzes.", "error")
        return redirect(url_for("instructor.questions"))

    question_text = request.form.get("question_text", "").strip()
    option_a = request.form.get("option_a", "").strip()
    option_b = request.form.get("option_b", "").strip()
    option_c = request.form.get("option_c", "").strip()
    option_d = request.form.get("option_d", "").strip()
    correct_option = request.form.get("correct_option", qs["correct_option"]).upper()
    marks = request.form.get("marks", qs["marks"], type=int)
    order_num = request.form.get("order_num", qs["order_num"], type=int)

    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("""
            UPDATE questions
            SET question_text = %s, option_a = %s, option_b = %s, option_c = %s, option_d = %s,
                correct_option = %s, marks = %s, order_num = %s
            WHERE id = %s
        """, (question_text, option_a, option_b, option_c, option_d, correct_option, marks, order_num, question_id))
        conn.commit()
        flash(f"Question #{question_id} updated successfully.", "success")
    except Exception as e:
        conn.rollback()
        flash(translate_db_error(e), "error")
    finally:
        cursor.close()
        conn.close()

    return redirect(url_for("instructor.questions"))


@instructor_bp.route("/questions/delete/<int:question_id>", methods=["POST"])
@instructor_required
def questions_delete(question_id):
    inst = get_current_instructor()
    qs = query_one("""
        SELECT qs.* FROM questions qs
        JOIN quizzes q ON qs.quiz_id = q.id
        JOIN modules m ON q.module_id = m.id
        JOIN courses c ON m.course_id = c.id
        WHERE qs.id = %s AND c.instructor_id = %s
    """, (question_id, inst["id"]))
    if not qs:
        flash("Permission denied: You can only delete questions in your own quizzes.", "error")
        return redirect(url_for("instructor.questions"))

    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("DELETE FROM questions WHERE id = %s", (question_id,))
        conn.commit()
        flash(f"Question #{question_id} deleted successfully.", "success")
    except Exception as e:
        conn.rollback()
        flash(translate_db_error(e), "error")
    finally:
        cursor.close()
        conn.close()

    return redirect(url_for("instructor.questions"))


# -----------------------------------------------------------------------------
# 7. STUDENT PROGRESS & ENROLMENTS (For this instructor's courses)
# -----------------------------------------------------------------------------
@instructor_bp.route("/learners")
@instructor_required
def learners():
    inst = get_current_instructor()
    learners_list = query_all("""
        SELECT vp.*
        FROM vw_learner_progress vp
        JOIN courses c ON vp.course_id = c.id
        WHERE c.instructor_id = %s
        ORDER BY vp.progress_pct DESC
    """, (inst["id"],))

    return render_template(
        "instructor/learners.html",
        active_page="inst_learners",
        instructor=inst,
        learners=learners_list
    )


@instructor_bp.route("/enrolments")
@instructor_required
def enrolments():
    inst = get_current_instructor()
    enrols = query_all("""
        SELECT e.*, u.name AS learner_name, u.email AS learner_email, c.title AS course_title
        FROM enrolments e
        JOIN learners l ON e.learner_id = l.id
        JOIN users u ON l.user_id = u.id
        JOIN courses c ON e.course_id = c.id
        WHERE c.instructor_id = %s
        ORDER BY e.enrolled_at DESC
    """, (inst["id"],))

    return render_template(
        "instructor/enrolments.html",
        active_page="inst_enrolments",
        instructor=inst,
        enrolments=enrols
    )


@instructor_bp.route("/attempts")
@instructor_required
def attempts():
    inst = get_current_instructor()
    attempts_list = query_all("""
        SELECT a.*, u.name AS learner_name, q.title AS quiz_title, c.title AS course_title
        FROM attempts a
        JOIN learners l ON a.learner_id = l.id
        JOIN users u ON l.user_id = u.id
        JOIN quizzes q ON a.quiz_id = q.id
        JOIN modules m ON q.module_id = m.id
        JOIN courses c ON m.course_id = c.id
        WHERE c.instructor_id = %s
        ORDER BY a.started_at DESC
    """, (inst["id"],))

    return render_template(
        "instructor/attempts.html",
        active_page="inst_attempts",
        instructor=inst,
        attempts=attempts_list
    )


@instructor_bp.route("/feedback")
@instructor_required
def feedback():
    inst = get_current_instructor()
    reviews = query_all("""
        SELECT f.*, u.name AS learner_name, c.title AS course_title
        FROM feedback f
        JOIN enrolments e ON f.enrolment_id = e.id
        JOIN learners l ON e.learner_id = l.id
        JOIN users u ON l.user_id = u.id
        JOIN courses c ON e.course_id = c.id
        WHERE c.instructor_id = %s
        ORDER BY f.created_at DESC
    """, (inst["id"],))

    return render_template(
        "instructor/feedback.html",
        active_page="inst_feedback",
        instructor=inst,
        feedback=reviews
    )
