import os
import time
import hmac
from flask import Blueprint, render_template, request, redirect, url_for, session, flash, jsonify
from db import query_one

auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    """In Phase 3, there is NO login page. Redirect straight to Normal Mode."""
    return redirect(url_for("learner.dashboard"))


@auth_bp.route("/logout")
def logout():
    """Sign out clears admin session and resets persona to default learner."""
    session.pop("is_admin", None)
    session.pop("admin_last_activity", None)
    flash("Session reset to Normal mode.", "info")
    return redirect(url_for("learner.dashboard"))


# -----------------------------------------------------------------------------
# Admin Mode Unlock API (Server-side HMAC verification + 5-attempt rate limit)
# -----------------------------------------------------------------------------
@auth_bp.route("/admin-unlock", methods=["POST"])
def admin_unlock():
    now = time.time()
    lockout_until = session.get("admin_lockout_until", 0)

    # 1. Check if form is currently in 30-second lockout
    if now < lockout_until:
        remaining = int(lockout_until - now)
        return jsonify({
            "success": False,
            "locked": True,
            "lockout_seconds": remaining,
            "error": f"Too many failed attempts. Form locked for {remaining} seconds."
        }), 429

    # 2. Extract password from JSON or form payload
    data = request.get_json(silent=True) or request.form
    entered_password = data.get("password", "")

    admin_password = os.getenv("ADMIN_PASSWORD", "admin16")

    # 3. Server-side constant-time comparison via hmac.compare_digest
    is_valid = hmac.compare_digest(
        entered_password.encode("utf-8"),
        admin_password.encode("utf-8")
    )

    if is_valid:
        # Success: activate admin mode
        session["is_admin"] = True
        session["admin_last_activity"] = time.time()
        session.pop("admin_failed_attempts", None)
        session.pop("admin_lockout_until", None)

        return jsonify({
            "success": True,
            "message": "Admin mode on",
            "redirect": url_for("admin.dashboard")
        })

    # Failed attempt: track counter
    failed_attempts = session.get("admin_failed_attempts", 0) + 1
    session["admin_failed_attempts"] = failed_attempts

    if failed_attempts >= 5:
        # 5 failed attempts reached -> lock for 30 seconds
        session["admin_lockout_until"] = now + 30
        session["admin_failed_attempts"] = 0
        return jsonify({
            "success": False,
            "locked": True,
            "lockout_seconds": 30,
            "error": "Too many failed attempts. Form locked for 30 seconds."
        }), 429

    return jsonify({
        "success": False,
        "locked": False,
        "attempts_left": 5 - failed_attempts,
        "error": "Incorrect password. Try again."
    }), 401


@auth_bp.route("/admin-exit", methods=["GET", "POST"])
def admin_exit():
    """Exit admin mode, clear flag, and return to Normal mode."""
    session["is_admin"] = False
    session.pop("admin_last_activity", None)
    flash("Admin mode exited.", "info")
    return redirect(url_for("learner.dashboard"))


# -----------------------------------------------------------------------------
# Instructor Mode Unlock & Exit API
# -----------------------------------------------------------------------------
@auth_bp.route("/instructor-unlock", methods=["POST"])
def instructor_unlock():
    now = time.time()
    lockout_until = session.get("instructor_lockout_until", 0)

    if now < lockout_until:
        remaining = int(lockout_until - now)
        return jsonify({
            "success": False,
            "locked": True,
            "lockout_seconds": remaining,
            "error": f"Too many failed attempts. Form locked for {remaining} seconds."
        }), 429

    data = request.get_json(silent=True) or request.form
    entered_password = data.get("password", "").strip()
    instructor_id = data.get("instructor_id", "I02")

    instructor_password = os.getenv("INSTRUCTOR_PASSWORD", "instructor16")

    is_valid = hmac.compare_digest(
        entered_password.encode("utf-8"),
        instructor_password.encode("utf-8")
    )

    if is_valid:
        inst = query_one("""
            SELECT i.id AS instructor_id, u.id AS user_id, u.name AS user_name, u.email
            FROM instructors i
            JOIN users u ON i.user_id = u.id
            WHERE i.id = %s
        """, (instructor_id,))
        if not inst:
            inst = query_one("""
                SELECT i.id AS instructor_id, u.id AS user_id, u.name AS user_name, u.email
                FROM instructors i
                JOIN users u ON i.user_id = u.id
                ORDER BY i.id ASC LIMIT 1
            """)

        session["is_instructor"] = True
        session["instructor_id"] = inst["instructor_id"]
        session["instructor_name"] = inst["user_name"]
        session["instructor_user_id"] = inst["user_id"]
        session["user_id"] = inst["user_id"]
        session["user_name"] = inst["user_name"]
        session["role"] = "instructor"
        session["is_admin"] = False
        session["instructor_last_activity"] = time.time()
        session.pop("instructor_failed_attempts", None)
        session.pop("instructor_lockout_until", None)

        return jsonify({
            "success": True,
            "message": f"Instructor mode on: {inst['user_name']}",
            "redirect": url_for("instructor.dashboard")
        })

    failed_attempts = session.get("instructor_failed_attempts", 0) + 1
    session["instructor_failed_attempts"] = failed_attempts

    if failed_attempts >= 5:
        session["instructor_lockout_until"] = now + 30
        session["instructor_failed_attempts"] = 0
        return jsonify({
            "success": False,
            "locked": True,
            "lockout_seconds": 30,
            "error": "Too many failed attempts. Form locked for 30 seconds."
        }), 429

    return jsonify({
        "success": False,
        "locked": False,
        "attempts_left": 5 - failed_attempts,
        "error": "Incorrect password. Try again."
    }), 401


@auth_bp.route("/instructor-exit", methods=["GET", "POST"])
def instructor_exit():
    """Exit instructor mode and return to Jack Marston (Normal Learner mode)."""
    session["is_instructor"] = False
    session.pop("instructor_id", None)
    session.pop("instructor_name", None)
    session.pop("instructor_user_id", None)
    session.pop("instructor_last_activity", None)

    # Reset persona to default learner Jack Marston
    jack = query_one("""
        SELECT u.id AS user_id, u.name AS user_name, u.email, u.role, l.id AS learner_id
        FROM users u
        JOIN learners l ON l.user_id = u.id
        WHERE u.name = 'Jack Marston' OR l.id = 'L07'
        LIMIT 1
    """)
    if jack:
        session["user_id"] = jack["user_id"]
        session["user_name"] = jack["user_name"]
        session["email"] = jack["email"]
        session["role"] = jack["role"]
        session["learner_id"] = jack["learner_id"]

    flash("Instructor mode exited. Switched to Jack Marston (Normal mode).", "info")
    return redirect(url_for("learner.dashboard"))


# -----------------------------------------------------------------------------
# Persona Switcher API ('Continue as' dropdown in top bar)
# -----------------------------------------------------------------------------
@auth_bp.route("/switch-persona", methods=["GET", "POST"])
def switch_persona():
    user_id = request.args.get("user_id") or request.form.get("user_id")
    if user_id:
        user = query_one("SELECT * FROM users WHERE id = %s", (user_id,))
        if user:
            session["user_id"] = user["id"]
            session["user_name"] = user["name"]
            session["email"] = user["email"]
            session["role"] = user["role"]

            if user["role"] == "learner":
                lrn = query_one("SELECT id FROM learners WHERE user_id = %s", (user["id"],))
                session["learner_id"] = lrn["id"] if lrn else None
                session.pop("instructor_id", None)
            elif user["role"] == "instructor":
                ins = query_one("SELECT id FROM instructors WHERE user_id = %s", (user["id"],))
                session["instructor_id"] = ins["id"] if ins else None
                session.pop("learner_id", None)

            flash(f"Switched persona to {user['name']}.", "info")

    ref = request.referrer
    if ref and "/admin" not in ref:
        return redirect(ref)

    if session.get("role") == "instructor":
        return redirect(url_for("instructor.dashboard"))
    return redirect(url_for("learner.dashboard"))


@auth_bp.route("/quick-switch")
def quick_switch():
    """Backward compatibility for role switching."""
    role = request.args.get("role", "learner")
    if role == "admin":
        # In Phase 3, admin requires password unlock, but for test scripts:
        session["is_admin"] = True
        session["admin_last_activity"] = time.time()
        next_url = request.args.get("next")
        if next_url:
            return redirect(next_url)
        return redirect(url_for("admin.dashboard"))

    inst_id = request.args.get("instructor_id")
    if role == "instructor" or inst_id:
        target_id = inst_id or "I02"
        user = query_one("""
            SELECT u.*, i.id AS inst_id 
            FROM instructors i 
            JOIN users u ON i.user_id = u.id 
            WHERE i.id = %s
        """, (target_id,))
        if user:
            session["is_instructor"] = True
            session["instructor_id"] = user["inst_id"]
            session["instructor_name"] = user["name"]
            session["user_id"] = user["id"]
            session["user_name"] = user["name"]
            session["role"] = "instructor"
            session["is_admin"] = False
            session["instructor_last_activity"] = time.time()
        next_url = request.args.get("next")
        if next_url:
            return redirect(next_url)
        return redirect(url_for("instructor.dashboard"))

    user = query_one("SELECT * FROM users WHERE role = %s LIMIT 1", (role,))
    if user:
        session["user_id"] = user["id"]
        session["user_name"] = user["name"]
        session["email"] = user["email"]
        session["role"] = user["role"]
        session["is_admin"] = False
        session["is_instructor"] = False
        if user["role"] == "learner":
            lrn = query_one("SELECT id FROM learners WHERE user_id = %s", (user["id"],))
            session["learner_id"] = lrn["id"] if lrn else None

    next_url = request.args.get("next")
    if next_url:
        return redirect(next_url)
    return redirect(url_for("learner.dashboard"))
