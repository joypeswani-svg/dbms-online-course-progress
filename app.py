import os
import time
from flask import Flask, redirect, url_for, session, render_template, request, flash
from dotenv import load_dotenv

load_dotenv()

from routes.auth import auth_bp
from routes.admin import admin_bp
from routes.instructor import instructor_bp
from routes.learner import learner_bp
from db import query_one, query_all
from table_service import get_all_table_counts, get_all_personas, ALL_TABLES, ALL_VIEWS

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "super-secret-key-change-in-production-linear-saas-2026")

# Register Blueprints
app.register_blueprint(auth_bp, url_prefix="/auth")
app.register_blueprint(admin_bp)
app.register_blueprint(instructor_bp)
app.register_blueprint(learner_bp)


@app.before_request
def setup_request_context():
    # 1. Admin inactivity timeout (30 minutes = 1800s)
    if session.get("is_admin"):
        last_activity = session.get("admin_last_activity", 0)
        if last_activity and (time.time() - last_activity > 1800):
            session["is_admin"] = False
            session.pop("admin_last_activity", None)
            flash("Admin mode session expired due to 30 minutes of inactivity.", "info")
        else:
            session["admin_last_activity"] = time.time()

    # 2. Instructor inactivity timeout (30 minutes = 1800s)
    if session.get("is_instructor"):
        last_activity = session.get("instructor_last_activity", 0)
        if last_activity and (time.time() - last_activity > 1800):
            session["is_instructor"] = False
            session.pop("instructor_last_activity", None)
            flash("Instructor mode session expired due to 30 minutes of inactivity.", "info")
        else:
            session["instructor_last_activity"] = time.time()

    # 3. Ensure default user session is Jack Marston (Normal Learner mode)
    if "user_id" not in session or session.get("user_name") in (None, "Maya Lin", ""):
        default_user = query_one("""
            SELECT u.id AS user_id, u.name AS user_name, u.email, u.role,
                   l.id AS learner_id
            FROM users u
            JOIN learners l ON l.user_id = u.id
            WHERE u.name = 'Jack Marston' OR l.id = 'L07'
            LIMIT 1
        """)
        if default_user:
            session["user_id"] = default_user["user_id"]
            session["user_name"] = default_user["user_name"]
            session["email"] = default_user["email"]
            session["role"] = default_user["role"]
            session["learner_id"] = default_user["learner_id"]
        session["is_admin"] = False
        session["is_instructor"] = False


@app.template_filter('initials')
def initials_filter(name):
    """Generate 2-letter uppercase initials for user avatars."""
    if not name:
        return 'JM'
    parts = str(name).strip().split()
    if len(parts) >= 2:
        return (parts[0][0] + parts[-1][0]).upper()
    return str(name)[:2].upper()


@app.context_processor
def inject_global_template_vars():
    """Inject table counts, instructor list, and mode flags to all templates."""
    counts = get_all_table_counts()
    all_instructors = query_all("""
        SELECT i.id, u.name, i.title, i.expertise
        FROM instructors i
        JOIN users u ON i.user_id = u.id
        ORDER BY i.id ASC
    """)

    return {
        "table_counts": counts,
        "all_tables": ALL_TABLES,
        "all_views": ALL_VIEWS,
        "all_instructors": all_instructors,
        "is_admin": session.get("is_admin", False),
        "is_instructor": session.get("is_instructor", False),
        "current_instructor_id": session.get("instructor_id", "I02"),
        "current_instructor_name": session.get("instructor_name", "Arthur Morgan"),
        "current_user_name": session.get("user_name", "Jack Marston"),
        "current_role": session.get("role", "learner")
    }


@app.route("/")
def index():
    if session.get("is_admin"):
        return redirect(url_for("admin.dashboard"))
    elif session.get("is_instructor"):
        return redirect(url_for("instructor.dashboard"))
    else:
        return redirect(url_for("learner.dashboard"))


# -----------------------------------------------------------------------------
# Standalone Printable & Verifiable Certificate Routes
# -----------------------------------------------------------------------------
@app.route("/certificates/view/<int:cert_id>")
def certificate_view(cert_id):
    cert = query_one("""
        SELECT cert.*, u.name AS learner_name, u.email AS learner_email,
               c.title AS course_title, inst_u.name AS instructor_name
        FROM certificates cert
        JOIN enrolments e ON cert.enrolment_id = e.id
        JOIN learners l ON e.learner_id = l.id
        JOIN users u ON l.user_id = u.id
        JOIN courses c ON e.course_id = c.id
        JOIN instructors inst ON c.instructor_id = inst.id
        JOIN users inst_u ON inst.user_id = inst_u.id
        WHERE cert.id = %s
    """, (cert_id,))
    if not cert:
        flash("Certificate not found.", "error")
        return redirect(url_for("learner.certificates"))
    return render_template("certificate_print.html", cert=cert)


@app.route("/verify/<cert_code>")
def certificate_verify(cert_code):
    cert = query_one("""
        SELECT cert.*, u.name AS learner_name, u.email AS learner_email,
               c.title AS course_title, inst_u.name AS instructor_name
        FROM certificates cert
        JOIN enrolments e ON cert.enrolment_id = e.id
        JOIN learners l ON e.learner_id = l.id
        JOIN users u ON l.user_id = u.id
        JOIN courses c ON e.course_id = c.id
        JOIN instructors inst ON c.instructor_id = inst.id
        JOIN users inst_u ON inst.user_id = inst_u.id
        WHERE cert.certificate_code = %s
    """, (cert_code,))
    if not cert:
        return "Certificate verification failed. Code not found.", 404
    return render_template("certificate_print.html", cert=cert)


# -----------------------------------------------------------------------------
# Error Handlers
# -----------------------------------------------------------------------------
@app.errorhandler(404)
def page_not_found(e):
    return redirect(url_for("index"))


if __name__ == "__main__":
    port = int(os.getenv("PORT", 5001))
    app.run(host="127.0.0.1", port=port, debug=True)
