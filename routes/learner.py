import json
from functools import wraps
from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from db import query_all, query_one, execute_stmt, get_db

learner_bp = Blueprint("learner", __name__, url_prefix="/learner")


def learner_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # In Phase 3, Normal mode is open to everyone
        return f(*args, **kwargs)
    return decorated_function


def get_current_learner_id():
    user_id = session.get("user_id")
    if user_id:
        lrn = query_one("SELECT id FROM learners WHERE user_id = %s", (user_id,))
        if lrn:
            return lrn["id"]
    # Fallback to first learner (L01)
    first_lrn = query_one("SELECT id FROM learners ORDER BY id ASC LIMIT 1")
    return first_lrn["id"] if first_lrn else "L01"


# -----------------------------------------------------------------------------
# 1. LEARNER DASHBOARD (MY LEARNING & CATALOG)
# -----------------------------------------------------------------------------
@learner_bp.route("/dashboard")
@learner_required
def dashboard():
    learner_id = get_current_learner_id()

    # My Enrolled Courses
    my_enrolments = query_all("""
        SELECT e.*, c.title, c.category, c.thumbnail_url, u.name AS instructor_name,
               (SELECT COUNT(*) FROM lessons les JOIN modules m ON les.module_id = m.id WHERE m.course_id = c.id) AS total_lessons,
               (SELECT COUNT(*) FROM lesson_progress lp WHERE lp.enrolment_id = e.id AND lp.is_completed = TRUE) AS completed_lessons
        FROM enrolments e
        JOIN courses c ON e.course_id = c.id
        JOIN instructors i ON c.instructor_id = i.id
        JOIN users u ON i.user_id = u.id
        WHERE e.learner_id = %s
        ORDER BY e.enrolled_at DESC
    """, (learner_id,))

    # Catalog Courses
    enrolled_course_ids = [e["course_id"] for e in my_enrolments]
    all_courses = query_all("""
        SELECT c.*, u.name AS instructor_name
        FROM courses c
        JOIN instructors i ON c.instructor_id = i.id
        JOIN users u ON i.user_id = u.id
        WHERE c.status = 'published'
        ORDER BY c.created_at DESC
    """)

    for c in all_courses:
        c["is_enrolled"] = c["id"] in enrolled_course_ids

    return render_template(
        "learner/dashboard.html",
        active_page="learner_dashboard",
        my_enrolments=my_enrolments,
        available_courses=all_courses
    )


# -----------------------------------------------------------------------------
# 2. ENROLL IN COURSE (CALLS STORED PROCEDURE enroll_learner)
# -----------------------------------------------------------------------------
@learner_bp.route("/enroll/<int:course_id>", methods=["POST"])
@learner_required
def enroll(course_id):
    learner_id = get_current_learner_id()

    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("CALL enroll_learner(%s, %s, @enr_id, @status_code, @msg)", (learner_id, course_id))
        cursor.execute("SELECT @enr_id AS enr_id, @status_code AS status_code, @msg AS msg")
        res = cursor.fetchone()
        conn.commit()

        if res["status_code"] == "SUCCESS":
            flash("Enrolled successfully! Welcome to the course.", "success")
            return redirect(url_for("learner.course_view", course_id=course_id))
        elif res["status_code"] == "ALREADY_ENROLLED":
            flash("You are already enrolled in this course.", "info")
            return redirect(url_for("learner.course_view", course_id=course_id))
        else:
            flash(f"Enrollment error: {res['msg']}", "error")
    except Exception as e:
        conn.rollback()
        flash(f"Database error during enrollment: {str(e)}", "error")
    finally:
        cursor.close()
        conn.close()

    return redirect(url_for("learner.dashboard"))


# -----------------------------------------------------------------------------
# 3. INTERACTIVE COURSE PLAYER
# -----------------------------------------------------------------------------
@learner_bp.route("/course/<int:course_id>")
@learner_required
def course_view(course_id):
    learner_id = get_current_learner_id()

    # Get enrollment
    enrolment = query_one("""
        SELECT e.*, c.title, c.category, c.passing_score, u.name AS instructor_name
        FROM enrolments e
        JOIN courses c ON e.course_id = c.id
        JOIN instructors i ON c.instructor_id = i.id
        JOIN users u ON i.user_id = u.id
        WHERE e.learner_id = %s AND e.course_id = %s
    """, (learner_id, course_id))

    if not enrolment:
        flash("Please enroll in this course first.", "info")
        return redirect(url_for("learner.dashboard"))

    # Load modules and lessons
    modules = query_all("SELECT * FROM modules WHERE course_id = %s ORDER BY order_num ASC", (course_id,))
    
    lesson_id_arg = request.args.get("lesson_id", type=int)
    active_lesson = None

    for m in modules:
        m["lessons"] = query_all("""
            SELECT l.*, COALESCE(lp.is_completed, FALSE) AS is_completed
            FROM lessons l
            LEFT JOIN lesson_progress lp ON l.id = lp.lesson_id AND lp.enrolment_id = %s
            WHERE l.module_id = %s
            ORDER BY l.order_num ASC
        """, (enrolment["id"], m["id"]))

        # Attach quizzes
        m["quizzes"] = query_all("""
            SELECT q.*, 
                   EXISTS(
                     SELECT 1 FROM attempts a 
                     WHERE a.quiz_id = q.id AND a.learner_id = %s AND a.is_passed = TRUE
                   ) AS is_passed
            FROM quizzes q
            WHERE q.module_id = %s
        """, (learner_id, m["id"]))

        # Find active lesson
        for les in m["lessons"]:
            if lesson_id_arg and les["id"] == lesson_id_arg:
                active_lesson = les
            elif not active_lesson and not les["is_completed"]:
                active_lesson = les

    # Fallback to first lesson if all completed
    if not active_lesson and modules and modules[0]["lessons"]:
        active_lesson = modules[0]["lessons"][0]

    # Check certificate if completed
    certificate = query_one("SELECT * FROM certificates WHERE enrolment_id = %s", (enrolment["id"],))

    return render_template(
        "learner/course_view.html",
        active_page="learner_dashboard",
        course=enrolment,
        enrolment=enrolment,
        modules=modules,
        active_lesson=active_lesson,
        certificate=certificate
    )


# -----------------------------------------------------------------------------
# 4. COMPLETE LESSON (CALLS STORED PROCEDURE complete_lesson)
# -----------------------------------------------------------------------------
@learner_bp.route("/lesson/complete/<int:enrolment_id>/<int:lesson_id>", methods=["POST"])
@learner_required
def complete_lesson(enrolment_id, lesson_id):
    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    try:
        # Call stored procedure complete_lesson
        cursor.execute("CALL complete_lesson(%s, %s, @new_prog, @is_done, @msg)", (enrolment_id, lesson_id))
        cursor.execute("SELECT @new_prog AS new_prog, @is_done AS is_done, @msg AS msg")
        res = cursor.fetchone()
        conn.commit()

        if res["is_done"]:
            flash(f"🎉 Fantastic work! You have finished all lessons. New progress: {res['new_prog']}%!", "success")
        else:
            flash(f"Lesson marked complete! Track progress updated to {res['new_prog']}%.", "success")
    except Exception as e:
        conn.rollback()
        flash(f"Error marking lesson complete: {str(e)}", "error")
    finally:
        cursor.close()
        conn.close()

    enr = query_one("SELECT course_id FROM enrolments WHERE id = %s", (enrolment_id,))
    return redirect(url_for("learner.course_view", course_id=enr["course_id"], lesson_id=lesson_id))


# -----------------------------------------------------------------------------
# 5. QUIZ PLAYER (CALLS STORED PROCEDURE submit_quiz_attempt)
# -----------------------------------------------------------------------------
@learner_bp.route("/quiz/<int:quiz_id>")
@learner_required
def quiz_view(quiz_id):
    learner_id = get_current_learner_id()

    quiz = query_one("""
        SELECT q.*, c.id AS course_id, c.title AS course_title, m.title AS module_title
        FROM quizzes q
        JOIN modules m ON q.module_id = m.id
        JOIN courses c ON m.course_id = c.id
        WHERE q.id = %s
    """, (quiz_id,))

    if not quiz:
        flash("Quiz not found.", "error")
        return redirect(url_for("learner.dashboard"))

    # Count existing attempts
    attempt_count = query_one("SELECT COUNT(*) AS c FROM attempts WHERE quiz_id = %s AND learner_id = %s", (quiz_id, learner_id))["c"]
    if attempt_count >= quiz["max_attempts"]:
        flash("Maximum quiz attempt limit reached for this assessment.", "error")
        return redirect(url_for("learner.course_view", course_id=quiz["course_id"]))

    questions = query_all("SELECT * FROM questions WHERE quiz_id = %s ORDER BY order_num ASC", (quiz_id,))

    return render_template(
        "learner/quiz_view.html",
        active_page="learner_dashboard",
        quiz=quiz,
        questions=questions,
        current_attempt_num=attempt_count + 1,
        remaining_attempts=quiz["max_attempts"] - attempt_count
    )


@learner_bp.route("/quiz/submit/<int:quiz_id>", methods=["POST"])
@learner_required
def quiz_submit(quiz_id):
    learner_id = get_current_learner_id()

    # Collect answers from form
    questions = query_all("SELECT id FROM questions WHERE quiz_id = %s", (quiz_id,))
    answers_list = []
    for q in questions:
        chosen = request.form.get(f"answer_{q['id']}")
        if chosen:
            answers_list.append({"question_id": q["id"], "chosen_option": chosen})

    answers_json = json.dumps(answers_list)

    # CALL submit_quiz_attempt STORED PROCEDURE!
    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("CALL submit_quiz_attempt(%s, %s, %s, @att_id, @score, @total, @passed, @msg)", (quiz_id, learner_id, answers_json))
        cursor.execute("SELECT @att_id AS att_id, @score AS score, @total AS total, @passed AS passed, @msg AS msg")
        res = cursor.fetchone()
        conn.commit()

        if res["att_id"]:
            if res["passed"]:
                flash("🎉 Congratulations! You passed the quiz assessment!", "success")
            else:
                flash("Quiz submitted. Passing score not reached.", "warning")
            return redirect(url_for("learner.quiz_result", attempt_id=res["att_id"]))
        else:
            flash(f"Submission rejected: {res['msg']}", "error")
            return redirect(url_for("learner.dashboard"))
    except Exception as e:
        conn.rollback()
        flash(f"Database error during quiz evaluation: {str(e)}", "error")
        return redirect(url_for("learner.dashboard"))
    finally:
        cursor.close()
        conn.close()


@learner_bp.route("/quiz/result/<int:attempt_id>")
@learner_required
def quiz_result(attempt_id):
    attempt = query_one("""
        SELECT a.*, q.title, q.total_marks, q.passing_marks, q.max_attempts,
               c.id AS course_id, c.title AS course_title
        FROM attempts a
        JOIN quizzes q ON a.quiz_id = q.id
        JOIN modules m ON q.module_id = m.id
        JOIN courses c ON m.course_id = c.id
        WHERE a.id = %s
    """, (attempt_id,))

    if not attempt:
        flash("Attempt record not found.", "error")
        return redirect(url_for("learner.dashboard"))

    responses = query_all("""
        SELECT r.*, q.question_text, q.correct_option
        FROM responses r
        JOIN questions q ON r.question_id = q.id
        WHERE r.attempt_id = %s
        ORDER BY q.order_num ASC
    """, (attempt_id,))

    remaining_attempts = max(0, attempt["max_attempts"] - attempt["attempt_number"])

    return render_template(
        "learner/quiz_result.html",
        active_page="learner_dashboard",
        quiz=attempt,
        attempt=attempt,
        score=attempt["score"],
        total_marks=attempt["total_marks"],
        is_passed=bool(attempt["is_passed"]),
        responses=responses,
        remaining_attempts=remaining_attempts
    )


# -----------------------------------------------------------------------------
# 6. MY CERTIFICATES GALLERY
# -----------------------------------------------------------------------------
@learner_bp.route("/certificates")
@learner_required
def certificates():
    learner_id = get_current_learner_id()

    cert_list = query_all("""
        SELECT cert.*, c.title AS course_title, u.name AS learner_name
        FROM certificates cert
        JOIN enrolments e ON cert.enrolment_id = e.id
        JOIN courses c ON e.course_id = c.id
        JOIN learners l ON e.learner_id = l.id
        JOIN users u ON l.user_id = u.id
        WHERE e.learner_id = %s
        ORDER BY cert.issued_at DESC
    """, (learner_id,))

    return render_template(
        "learner/certificates.html",
        active_page="learner_certificates",
        certificates=cert_list
    )


# -----------------------------------------------------------------------------
# 7. SUBMIT COURSE FEEDBACK
# -----------------------------------------------------------------------------
@learner_bp.route("/feedback/<int:enrolment_id>", methods=["POST"])
@learner_required
def feedback(enrolment_id):
    rating = int(request.form.get("rating", 5))
    review_title = request.form.get("review_title", "").strip()
    comments = request.form.get("comments", "").strip()

    try:
        execute_stmt("""
            INSERT INTO feedback (enrolment_id, rating, review_title, comments)
            VALUES (%s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE rating = %s, review_title = %s, comments = %s
        """, (enrolment_id, rating, review_title, comments, rating, review_title, comments))
        flash("Thank you! Your feedback has been recorded.", "success")
    except Exception as e:
        flash(f"Error submitting feedback: {str(e)}", "error")

    enr = query_one("SELECT course_id FROM enrolments WHERE id = %s", (enrolment_id,))
    return redirect(url_for("learner.course_view", course_id=enr["course_id"]))
