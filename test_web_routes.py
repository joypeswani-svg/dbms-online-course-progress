#!/usr/bin/env python3
"""
Automated Test Suite for LearnPulse SaaS Web Application.
Validates all endpoints, role sessions, procedures, CSV exports, and security rules.
"""

from app import app

def test_all_routes():
    client = app.test_client()

    print("\n" + "=" * 70)
    print("RUNNING END-TO-END WEB APPLICATION ROUTE AUDIT")
    print("=" * 70)

    # 1. Login Page
    res = client.get("/auth/login")
    assert res.status_code == 200, f"Expected 200 but got {res.status_code}"
    print("✓ [GET /auth/login] 200 OK")

    # 2. Admin Authentication
    res = client.post("/auth/login", data={"email": "admin@learnpulse.io", "password": "admin123"}, follow_redirects=True)
    assert res.status_code == 200
    assert b"System Executive Dashboard" in res.data
    print("✓ [POST /auth/login] Admin authenticated successfully")

    # 3. Admin Pages
    pages = [
        ("/admin/dashboard", b"Enrolments per Course"),
        ("/admin/users", b"Users & Team Management"),
        ("/admin/courses", b"Courses & Curriculum"),
        ("/admin/courses/1", b"Curriculum Structure"),
        ("/admin/quizzes", b"Assessment & Question Builder"),
        ("/admin/enrolments", b"Student Course Enrolments"),
        ("/admin/attempts", b"Quiz Attempts & Responses Audit"),
        ("/admin/certificates", b"Credentials & Certification Issuance"),
        ("/admin/feedback", b"Student Feedback & Ratings"),
        ("/admin/reports", b"Analytical Intelligence & Database Views"),
        ("/admin/reports/export?view=course_completion", b"course_id,course_title"),
    ]

    for path, expected_text in pages:
        res = client.get(path)
        assert res.status_code == 200, f"Failed on {path}: status {res.status_code}"
        assert expected_text in res.data, f"Failed on {path}: expected text not found"
        print(f"✓ [GET {path}] 200 OK")

    # 4. SQL Console Valid SELECT Query
    res = client.post("/admin/sql-console", data={"sql_query": "SELECT id, title, price FROM courses LIMIT 3;"}, follow_redirects=True)
    assert res.status_code == 200
    assert b"Query Results" in res.data
    print("✓ [POST /admin/sql-console] SELECT query executed and returned formatted table")

    # 5. SQL Console Blocked Mutation Query (Security Check)
    res = client.post("/admin/sql-console", data={"sql_query": "DROP TABLE users;"}, follow_redirects=True)
    assert res.status_code == 200
    assert b"Security Policy Violation" in res.data
    print("✓ [POST /admin/sql-console] Prohibited DROP query blocked by security guard")

    # 6. Instructor Persona
    client.get("/auth/quick-switch?role=instructor", follow_redirects=True)
    res = client.get("/instructor/dashboard")
    assert res.status_code == 200
    assert b"Instructor Studio" in res.data
    print("✓ [GET /instructor/dashboard] 200 OK")

    res = client.get("/instructor/learners")
    assert res.status_code == 200
    assert b"Student Progress Tracking" in res.data
    print("✓ [GET /instructor/learners] 200 OK")

    # 7. Learner Persona
    client.get("/auth/quick-switch?role=learner", follow_redirects=True)
    res = client.get("/learner/dashboard")
    assert res.status_code == 200
    assert b"My Active Courses" in res.data
    print("✓ [GET /learner/dashboard] 200 OK")

    res = client.get("/learner/course/1")
    assert res.status_code == 200
    assert b"Curriculum Syllabus" in res.data
    print("✓ [GET /learner/course/1] 200 OK")

    res = client.get("/learner/certificates")
    assert res.status_code == 200
    assert b"My Verified Credentials" in res.data
    print("✓ [GET /learner/certificates] 200 OK")

    # 8. Printable Certificate
    res = client.get("/certificates/view/1")
    assert res.status_code == 200
    assert b"Certificate of Completion" in res.data
    assert b"LP-2025-A9E4-71F2" in res.data
    print("✓ [GET /certificates/view/1] 200 OK (Printable Certificate Verified)")

    print("\n" + "=" * 70)
    print("🎉 ALL 18 WEB APPLICATION TESTS PASSED FLAWLESSLY!")
    print("=" * 70)

if __name__ == "__main__":
    test_all_routes()
