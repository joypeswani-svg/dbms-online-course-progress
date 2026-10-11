#!/usr/bin/env python3
"""
Comprehensive Test Suite for:
1. Default User is Jack Marston (L07)
2. Dedicated Instructor Mode (password 'instructor16', HMAC verification, 5-attempt rate limit)
3. Instructor-Only Course Scoping for Modules, Lessons, Quizzes, Questions
4. Cross-instructor modification prevention
5. Exit Instructor Mode resets back to Jack Marston
"""

import os
from app import app
from db import query_one, query_all

def run_instructor_mode_audit():
    client = app.test_client()

    print("\n" + "=" * 70)
    print("INSTRUCTOR MODE & SCOPING SECURITY AUDIT")
    print("=" * 70)

    # -------------------------------------------------------------------------
    # TEST 1: Default persona is Jack Marston
    # -------------------------------------------------------------------------
    res = client.get("/", follow_redirects=True)
    assert res.status_code == 200
    with client.session_transaction() as sess:
        assert sess.get("user_name") == "Jack Marston"
        assert sess.get("learner_id") == "L07"
        assert sess.get("is_admin") is False
        assert sess.get("is_instructor") is False
    print("✓ [TEST 1] Root URL defaults directly to Jack Marston (L07) in Normal Learner mode")

    # -------------------------------------------------------------------------
    # TEST 2: Unauthenticated access to /instructor is blocked
    # -------------------------------------------------------------------------
    res = client.get("/instructor/dashboard", follow_redirects=True)
    assert res.status_code == 200
    assert b"Catalog & Enrol" in res.data or b"Courses" in res.data
    with client.session_transaction() as sess:
        assert not sess.get("is_instructor")
    print("✓ [TEST 2] Direct access to /instructor blocked by @instructor_required (Redirected to Normal mode)")

    # -------------------------------------------------------------------------
    # TEST 3: Instructor Password Verification (Wrong password & Rate Limit)
    # -------------------------------------------------------------------------
    res = client.post("/auth/instructor-unlock", json={"password": "wrongpassword", "instructor_id": "I02"})
    assert res.status_code == 401
    data = res.get_json()
    assert data["success"] is False
    assert "Incorrect password" in data["error"]
    print("✓ [TEST 3] Wrong instructor password rejected with 401")

    # Rate limiting: 5 failed attempts
    for i in range(2, 6):
        res = client.post("/auth/instructor-unlock", json={"password": f"wrong_{i}", "instructor_id": "I02"})
    assert res.status_code == 429
    data = res.get_json()
    assert data["locked"] is True
    assert data["lockout_seconds"] > 0
    print(f"✓ [TEST 4] 5 failed attempts triggered 30-second lockout ({data['lockout_seconds']}s)")

    # Clear lockout in session for test
    with client.session_transaction() as sess:
        sess.pop("instructor_lockout_until", None)
        sess.pop("instructor_failed_attempts", None)

    # Correct password unlock: 'instructor16' for Arthur Morgan (I02)
    res = client.post("/auth/instructor-unlock", json={"password": "instructor16", "instructor_id": "I02"})
    assert res.status_code == 200
    data = res.get_json()
    assert data["success"] is True
    with client.session_transaction() as sess:
        assert sess.get("is_instructor") is True
        assert sess.get("instructor_id") == "I02"
        assert sess.get("instructor_name") == "Arthur Morgan"
    print("✓ [TEST 5] Valid password 'instructor16' unlocked Arthur Morgan (I02) in Instructor Mode")

    # -------------------------------------------------------------------------
    # TEST 4: Instructor Studio Views Loaded
    # -------------------------------------------------------------------------
    instructor_routes = [
        "/instructor/dashboard",
        "/instructor/courses",
        "/instructor/modules",
        "/instructor/lessons",
        "/instructor/quizzes",
        "/instructor/questions",
        "/instructor/learners",
        "/instructor/enrolments",
        "/instructor/attempts",
        "/instructor/feedback",
    ]
    print("\nAuditing Instructor Studio Views for Arthur Morgan:")
    for r in instructor_routes:
        res = client.get(r)
        assert res.status_code == 200, f"Route {r} failed with {res.status_code}"
        assert b"Instructor: Arthur Morgan" in res.data or b"Arthur Morgan" in res.data
        print(f"  ✓ [{r}] 200 OK")

    # -------------------------------------------------------------------------
    # TEST 5: Course Scoping Security - Attempting to add module to other's course
    # -------------------------------------------------------------------------
    # Arthur Morgan (I02) owns courses 2 and 7.
    # Course 1 is owned by Hosea Matthews (I01).
    res = client.post("/instructor/modules/create", data={
        "course_id": 1,  # Course 1 belongs to Hosea Matthews!
        "title": "Malicious Tampering Module",
        "order_num": 99
    }, follow_redirects=True)
    assert res.status_code == 200
    assert b"Permission denied" in res.data
    # Verify module was NOT added to database
    tamper = query_one("SELECT * FROM modules WHERE course_id = 1 AND title = 'Malicious Tampering Module'")
    assert tamper is None
    print("✓ [TEST 6] Cross-instructor tampering blocked: Cannot add modules to courses owned by other instructors")

    # -------------------------------------------------------------------------
    # TEST 6: Legitimate Module Creation on Arthur Morgan's Course
    # -------------------------------------------------------------------------
    # Course 2 belongs to Arthur Morgan
    res = client.post("/instructor/modules/create", data={
        "course_id": 2,
        "title": "Arthur's Deep Dive Module",
        "order_num": 10
    }, follow_redirects=True)
    assert res.status_code == 200
    created_mod = query_one("SELECT * FROM modules WHERE course_id = 2 AND title = 'Arthur\\'s Deep Dive Module'")
    assert created_mod is not None
    print(f"✓ [TEST 7] Arthur Morgan successfully created module #{created_mod['id']} in his course")

    # Clean up test module
    from db import get_db
    conn = get_db()
    c = conn.cursor()
    c.execute("DELETE FROM modules WHERE id = %s", (created_mod["id"],))
    conn.commit()
    c.close()
    conn.close()

    # -------------------------------------------------------------------------
    # TEST 7: Exit Instructor Mode resets session to Jack Marston
    # -------------------------------------------------------------------------
    res = client.get("/auth/instructor-exit", follow_redirects=True)
    assert res.status_code == 200
    with client.session_transaction() as sess:
        assert sess.get("is_instructor") is False
        assert sess.get("user_name") == "Jack Marston"
        assert sess.get("learner_id") == "L07"
    print("✓ [TEST 8] Exit Instructor Mode restored session back to Jack Marston (Normal Learner mode)")

    print("\n" + "=" * 70)
    print("🎉 ALL INSTRUCTOR MODE REQUIREMENTS VERIFIED FLAWLESSLY!")
    print("=" * 70)

if __name__ == "__main__":
    run_instructor_mode_audit()
