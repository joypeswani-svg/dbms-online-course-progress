"""
Table Browser Service for LearnPulse SaaS.
Provides introspection, schema querying, FK resolution, and CRUD operations
across all 14 MySQL database tables and 6 views.
"""

import re
import hashlib
from typing import Dict, Any, List, Tuple, Optional
import mysql.connector
from db import query_all, query_one, execute_stmt, get_db

ALL_TABLES = [
    "users",
    "instructors",
    "learners",
    "courses",
    "modules",
    "lessons",
    "enrolments",
    "lesson_progress",
    "quizzes",
    "questions",
    "attempts",
    "responses",
    "certificates",
    "feedback"
]

ALL_VIEWS = [
    "vw_learner_progress",
    "vw_course_completion",
    "vw_dropout_report",
    "vw_quiz_performance",
    "vw_certificate_eligibility",
    "vw_instructor_summary"
]

# CHECK constraints and UI helper hints per column
CHECK_HINTS = {
    "users.email": "Must be a valid email format (e.g. name@domain.com)",
    "courses.price": "Must be greater than or equal to 0.00",
    "courses.passing_score": "Standard passing score percentage (default 70)",
    "enrolments.progress": "Must be between 0 and 100 percent (enforced by CHECK constraint)",
    "attempts.score": "Must be between 0 and quiz total marks",
    "attempts.percentage": "Must be between 0 and 100 percent",
    "feedback.rating": "Must be an integer rating between 1 and 5 stars",
    "quizzes.max_attempts": "Attempt limit per learner (enforced by trigger)",
    "quizzes.passing_score": "Passing threshold out of 100",
}


def get_all_table_counts() -> Dict[str, int]:
    """Return live row counts for all 14 tables in a single fast query."""
    union_parts = [f"SELECT '{t}' AS tbl, COUNT(*) AS cnt FROM `{t}`" for t in ALL_TABLES]
    sql = " UNION ALL ".join(union_parts)
    try:
        rows = query_all(sql)
        return {r["tbl"]: r["cnt"] for r in rows}
    except Exception:
        # Fallback if DB is resetting
        return {t: 0 for t in ALL_TABLES}


def get_all_personas() -> List[Dict[str, Any]]:
    """Return all learners and instructors for the 'Continue as' persona switcher."""
    return query_all("""
        SELECT u.id, u.name, u.email, u.role,
               COALESCE(l.headline, i.title, 'System User') AS subtitle
        FROM users u
        LEFT JOIN learners l ON u.id = l.user_id
        LEFT JOIN instructors i ON u.id = i.user_id
        WHERE u.role IN ('learner', 'instructor')
        ORDER BY u.role DESC, u.name ASC
    """)


def get_table_schema(table_name: str) -> Dict[str, Any]:
    """Introspect INFORMATION_SCHEMA for table columns, keys, constraints, and indexes."""
    if table_name not in ALL_TABLES and table_name not in ALL_VIEWS:
        raise ValueError(f"Unknown table or view: {table_name}")

    # 1. Columns
    col_rows = query_all("""
        SELECT COLUMN_NAME, DATA_TYPE, COLUMN_TYPE, IS_NULLABLE,
               COLUMN_DEFAULT, EXTRA, COLUMN_KEY, COLUMN_COMMENT
        FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = %s
        ORDER BY ORDINAL_POSITION
    """, (table_name,))

    # 2. Foreign keys for this table
    fk_rows = query_all("""
        SELECT COLUMN_NAME, REFERENCED_TABLE_NAME, REFERENCED_COLUMN_NAME
        FROM INFORMATION_SCHEMA.KEY_COLUMN_USAGE
        WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = %s
          AND REFERENCED_TABLE_NAME IS NOT NULL
    """, (table_name,))

    fk_map = {r["COLUMN_NAME"]: {"ref_table": r["REFERENCED_TABLE_NAME"], "ref_col": r["REFERENCED_COLUMN_NAME"]} for r in fk_rows}

    # 3. Indexes
    idx_rows = query_all("""
        SELECT INDEX_NAME, COLUMN_NAME, NON_UNIQUE, INDEX_TYPE
        FROM INFORMATION_SCHEMA.STATISTICS
        WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = %s
        ORDER BY INDEX_NAME, SEQ_IN_INDEX
    """, (table_name,))

    # 4. Parse ENUM values and field types
    columns = []
    primary_key = col_rows[0]["COLUMN_NAME"] if col_rows else "id"
    for r in col_rows:
        col_name = r["COLUMN_NAME"]
        data_type = r["DATA_TYPE"]
        col_type = r["COLUMN_TYPE"]
        is_pk = (r["COLUMN_KEY"] == "PRI")
        if is_pk:
            primary_key = col_name

        enum_values = []
        if data_type == "enum":
            # Extract 'val1','val2' from enum('val1','val2')
            match = re.findall(r"'([^']*)'", col_type)
            if match:
                enum_values = match

        fk_info = fk_map.get(col_name)
        hint = CHECK_HINTS.get(f"{table_name}.{col_name}", "")

        columns.append({
            "name": col_name,
            "data_type": data_type,
            "col_type": col_type,
            "nullable": (r["IS_NULLABLE"] == "YES"),
            "default": r["COLUMN_DEFAULT"],
            "extra": r["EXTRA"],
            "is_pk": is_pk,
            "is_fk": bool(fk_info),
            "fk_info": fk_info,
            "enum_values": enum_values,
            "hint": hint
        })

    return {
        "table_name": table_name,
        "is_view": table_name in ALL_VIEWS,
        "primary_key": primary_key,
        "columns": columns,
        "indexes": idx_rows,
        "foreign_keys": fk_map
    }


def get_fk_options_for_table(table_name: str) -> Dict[str, List[Dict[str, Any]]]:
    """Retrieve human-readable options for all foreign key fields of a table."""
    options = {}

    if table_name in ("instructors", "learners"):
        # user_id -> users
        users = query_all("SELECT id, name, email FROM users ORDER BY name ASC")
        options["user_id"] = [{"id": u["id"], "label": f"{u['name']} ({u['email']})"} for u in users]

    elif table_name == "courses":
        # instructor_id -> instructors (joined to users)
        insts = query_all("""
            SELECT i.id, u.name, i.title
            FROM instructors i
            JOIN users u ON i.user_id = u.id
            ORDER BY u.name ASC
        """)
        options["instructor_id"] = [{"id": i["id"], "label": f"{i['name']} — {i['title']}"} for i in insts]

    elif table_name == "modules":
        # course_id -> courses
        courses = query_all("SELECT id, title FROM courses ORDER BY title ASC")
        options["course_id"] = [{"id": c["id"], "label": c["title"]} for c in courses]

    elif table_name == "lessons":
        # module_id -> modules
        mods = query_all("""
            SELECT m.id, m.title, c.title AS course_title
            FROM modules m
            JOIN courses c ON m.course_id = c.id
            ORDER BY c.title ASC, m.order_num ASC
        """)
        options["module_id"] = [{"id": m["id"], "label": f"{m['course_title']} > {m['title']}"} for m in mods]

    elif table_name == "enrolments":
        # learner_id, course_id
        lrns = query_all("SELECT l.id, u.name, u.email FROM learners l JOIN users u ON l.user_id = u.id ORDER BY u.name ASC")
        options["learner_id"] = [{"id": l["id"], "label": f"{l['name']} ({l['email']})"} for l in lrns]
        courses = query_all("SELECT id, title FROM courses ORDER BY title ASC")
        options["course_id"] = [{"id": c["id"], "label": c["title"]} for c in courses]

    elif table_name == "lesson_progress":
        enrols = query_all("""
            SELECT e.id, u.name AS learner_name, c.title AS course_title
            FROM enrolments e
            JOIN learners l ON e.learner_id = l.id
            JOIN users u ON l.user_id = u.id
            JOIN courses c ON e.course_id = c.id
            ORDER BY e.id DESC
        """)
        options["enrolment_id"] = [{"id": e["id"], "label": f"#{e['id']} {e['learner_name']} — {e['course_title']}"} for e in enrols]
        lessons = query_all("SELECT id, title FROM lessons ORDER BY title ASC")
        options["lesson_id"] = [{"id": l["id"], "label": l["title"]} for l in lessons]

    elif table_name == "quizzes":
        courses = query_all("SELECT id, title FROM courses ORDER BY title ASC")
        options["course_id"] = [{"id": c["id"], "label": c["title"]} for c in courses]

    elif table_name == "questions":
        quizzes = query_all("SELECT id, title FROM quizzes ORDER BY title ASC")
        options["quiz_id"] = [{"id": q["id"], "label": q["title"]} for q in quizzes]

    elif table_name == "attempts":
        quizzes = query_all("SELECT id, title FROM quizzes ORDER BY title ASC")
        options["quiz_id"] = [{"id": q["id"], "label": q["title"]} for q in quizzes]
        lrns = query_all("SELECT l.id, u.name FROM learners l JOIN users u ON l.user_id = u.id ORDER BY u.name ASC")
        options["learner_id"] = [{"id": l["id"], "label": l["name"]} for l in lrns]

    elif table_name == "responses":
        attms = query_all("""
            SELECT a.id, u.name AS learner_name, q.title AS quiz_title
            FROM attempts a
            JOIN learners l ON a.learner_id = l.id
            JOIN users u ON l.user_id = u.id
            JOIN quizzes q ON a.quiz_id = q.id
            ORDER BY a.id DESC
        """)
        options["attempt_id"] = [{"id": a["id"], "label": f"Attempt #{a['id']} by {a['learner_name']} ({a['quiz_title']})"} for a in attms]
        questions = query_all("SELECT id, question_text FROM questions ORDER BY id ASC")
        options["question_id"] = [{"id": q["id"], "label": f"Q{q['id']}: {q['question_text'][:60]}..."} for q in questions]

    elif table_name == "certificates":
        enrols = query_all("""
            SELECT e.id, u.name AS learner_name, c.title AS course_title
            FROM enrolments e
            JOIN learners l ON e.learner_id = l.id
            JOIN users u ON l.user_id = u.id
            JOIN courses c ON e.course_id = c.id
            ORDER BY e.id DESC
        """)
        options["enrolment_id"] = [{"id": e["id"], "label": f"Enrolment #{e['id']} — {e['learner_name']} ({e['course_title']})"} for e in enrols]

    elif table_name == "feedback":
        enrols = query_all("""
            SELECT e.id, u.name AS learner_name, c.title AS course_title
            FROM enrolments e
            JOIN learners l ON e.learner_id = l.id
            JOIN users u ON l.user_id = u.id
            JOIN courses c ON e.course_id = c.id
            ORDER BY e.id DESC
        """)
        options["enrolment_id"] = [{"id": e["id"], "label": f"Enrolment #{e['id']} — {e['learner_name']}"} for e in enrols]
        lrns = query_all("SELECT l.id, u.name FROM learners l JOIN users u ON l.user_id = u.id ORDER BY u.name ASC")
        options["learner_id"] = [{"id": l["id"], "label": l["name"]} for l in lrns]
        courses = query_all("SELECT id, title FROM courses ORDER BY title ASC")
        options["course_id"] = [{"id": c["id"], "label": c["title"]} for c in courses]

    return options


def get_table_data(
    table_name: str,
    page: int = 1,
    per_page: int = 15,
    search: str = "",
    sort_col: str = "",
    sort_dir: str = "asc"
) -> Tuple[List[Dict[str, Any]], int, int, List[str]]:
    """
    Fetch paginated rows from table_name with searchable filtering, sorting,
    and foreign-key label resolution for display.
    """
    schema = get_table_schema(table_name)
    columns = [c["name"] for c in schema["columns"]]
    pk_col = schema["primary_key"]

    # Validate sort column
    if not sort_col or sort_col not in columns:
        sort_col = pk_col
    sort_dir = "DESC" if sort_dir.lower() == "desc" else "ASC"

    # Search condition across text/varchar/int columns
    where_clauses = []
    params = []
    if search:
        search_terms = []
        for col in schema["columns"]:
            if col["data_type"] in ("varchar", "text", "enum", "char"):
                search_terms.append(f"`{col['name']}` LIKE %s")
                params.append(f"%{search}%")
            elif col["data_type"] in ("int", "bigint", "tinyint") and search.isdigit():
                search_terms.append(f"`{col['name']}` = %s")
                params.append(int(search))
        if search_terms:
            where_clauses.append(f"({' OR '.join(search_terms)})")

    where_sql = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""

    # Total row count
    count_sql = f"SELECT COUNT(*) AS total FROM `{table_name}` {where_sql}"
    total_row = query_one(count_sql, tuple(params))
    total_rows = total_row["total"] if total_row else 0
    total_pages = max(1, (total_rows + per_page - 1) // per_page)
    page = max(1, min(page, total_pages))
    offset = (page - 1) * per_page

    # Query rows
    query_sql = f"SELECT * FROM `{table_name}` {where_sql} ORDER BY `{sort_col}` {sort_dir} LIMIT %s OFFSET %s"
    fetch_params = list(params) + [per_page, offset]
    rows = query_all(query_sql, tuple(fetch_params))

    # Resolve Foreign Key display labels
    fk_options = get_fk_options_for_table(table_name)
    fk_lookup = {}
    for fk_col, opts in fk_options.items():
        fk_lookup[fk_col] = {opt["id"]: opt["label"] for opt in opts}

    for r in rows:
        r["_fk_display"] = {}
        for fk_col, id_map in fk_lookup.items():
            val = r.get(fk_col)
            if val is not None and val in id_map:
                r["_fk_display"][fk_col] = id_map[val]
            elif val is not None:
                r["_fk_display"][fk_col] = str(val)

    return rows, total_rows, total_pages, columns


def translate_db_error(e: Exception) -> str:
    """Translate MySQL connector exceptions into clean, friendly human messages."""
    msg = str(e)
    errno = getattr(e, "errno", None)

    if errno == 1062 or "Duplicate entry" in msg:
        if "uq_enrolments_learner_course" in msg or "learner_id" in msg and "course_id" in msg:
            return "Duplicate enrolment rejected: This learner is already registered in this course."
        if "uq_users_email" in msg:
            return "Duplicate email rejected: A user with this email address already exists."
        if "uq_instructors_user_id" in msg or "uq_learners_user_id" in msg:
            return "This user already has an active profile of this type."
        if "uq_certificates_enrolment_id" in msg:
            return "A certificate has already been issued for this enrolment."
        return "Duplicate record rejected: A record with this unique value already exists."

    if errno == 3819 or "chk_enrolments_progress" in msg or "Check constraint" in msg:
        if "progress" in msg:
            return "Invalid progress rejected: Course progress must be between 0 and 100 percent."
        if "rating" in msg:
            return "Invalid rating rejected: Feedback rating must be between 1 and 5 stars."
        if "score" in msg:
            return "Invalid score: Score must be non-negative and not exceed total marks."
        return "Check constraint violation: The submitted values violate table validation constraints."

    if errno == 1644 or "SQLSTATE '45000'" in msg:
        if "attempt limit" in msg.lower() or "trg_check_quiz_attempt_limit" in msg:
            return "Quiz attempt limit exceeded: This learner has reached the maximum allowed attempts for this quiz."
        if "ineligible" in msg.lower() or "trg_check_certificate_eligibility" in msg or "certificate" in msg.lower():
            return "Certificate issuance blocked: Learner is ineligible (requires 100% lesson progress and passing score on all quizzes)."
        # Extract custom signal message
        match = re.search(r"MESSAGE_TEXT = '([^']*)'", msg) or re.search(r"1644 \([0-9A-Z]+\): (.*)", msg)
        if match:
            return match.group(1)
        return "Operation blocked by database business rule trigger."

    if errno == 1451 or "foreign key constraint fails" in msg and "delete" in msg.lower():
        return "Cannot delete this record: Active dependent records exist in other tables (foreign key restriction). Remove dependent records first."

    if errno == 1452 or "foreign key constraint fails" in msg and ("insert" in msg.lower() or "update" in msg.lower()):
        return "Invalid relationship: The referenced foreign key record does not exist."

    # Generic friendly fallback without cryptic SQL codes
    return f"Database operation failed: {msg.split(':')[-1].strip()}"


def generate_next_prefixed_id(table_name: str, prefix: str) -> str:
    """Find highest numeric ID with prefix and return next e.g. L21, I06, A02."""
    rows = query_all(f"SELECT id FROM `{table_name}` WHERE id LIKE %s", (f"{prefix}%",))
    max_num = 0
    for r in rows:
        suffix = str(r["id"])[len(prefix):]
        if suffix.isdigit():
            max_num = max(max_num, int(suffix))
    next_num = max_num + 1
    return f"{prefix}{next_num:02d}"


def insert_row(table_name: str, form_data: Dict[str, Any]) -> Tuple[bool, str, Optional[Any]]:
    """Insert a new record into table_name using parameterized SQL."""
    schema = get_table_schema(table_name)
    pk_col = schema["primary_key"]

    fields = []
    placeholders = []
    values = []

    for col in schema["columns"]:
        col_name = col["name"]
        # Skip auto increment primary key
        if col["is_pk"] and "auto_increment" in col["extra"].lower():
            continue

        raw_val = form_data.get(col_name)

        # Auto-generate role-prefixed PK if not provided
        if col["is_pk"] and (raw_val is None or raw_val == ""):
            if table_name == "learners":
                raw_val = generate_next_prefixed_id("learners", "L")
            elif table_name == "instructors":
                raw_val = generate_next_prefixed_id("instructors", "I")
            elif table_name == "users":
                role = form_data.get("role", "learner")
                prefix = "A" if role == "admin" else ("I" if role == "instructor" else "L")
                raw_val = generate_next_prefixed_id("users", prefix)

        # Handle password hashing for users
        if table_name == "users" and col_name == "password_hash":
            pwd = form_data.get("password") or raw_val or "learner123"
            raw_val = hashlib.sha256(pwd.encode("utf-8")).hexdigest()

        if raw_val is None or raw_val == "":
            if col["nullable"]:
                val = None
            elif col["default"] is not None:
                continue  # Let default handle it
            else:
                return False, f"Field '{col_name}' is required.", None
        else:
            # Type casting
            dt = col["data_type"]
            try:
                if dt in ("int", "tinyint", "bigint"):
                    val = int(raw_val)
                elif dt in ("decimal", "float", "double"):
                    val = float(raw_val)
                elif dt == "tinyint" and col["col_type"].startswith("tinyint(1)"):
                    val = True if str(raw_val).lower() in ("true", "1", "on", "yes") else False
                else:
                    val = str(raw_val).strip()
            except ValueError:
                return False, f"Invalid value for numeric field '{col_name}'.", None

        fields.append(f"`{col_name}`")
        placeholders.append("%s")
        values.append(val)

    if not fields:
        return False, "No data fields provided.", None

    sql = f"INSERT INTO `{table_name}` ({', '.join(fields)}) VALUES ({', '.join(placeholders)})"
    try:
        res = execute_stmt(sql, tuple(values))
        return True, "Record created successfully.", res.get("last_id")
    except Exception as e:
        return False, translate_db_error(e), None


def update_row(table_name: str, record_id: Any, form_data: Dict[str, Any]) -> Tuple[bool, str]:
    """Update an existing record in table_name using parameterized SQL."""
    schema = get_table_schema(table_name)
    pk_col = schema["primary_key"]

    assignments = []
    values = []

    for col in schema["columns"]:
        col_name = col["name"]
        if col["is_pk"]:
            continue

        # Skip password update if empty
        if table_name == "users" and col_name == "password_hash":
            new_pwd = form_data.get("new_password") or form_data.get("password")
            if new_pwd:
                hashed = hashlib.sha256(new_pwd.encode("utf-8")).hexdigest()
                assignments.append(f"`password_hash` = %s")
                values.append(hashed)
            continue

        if col_name not in form_data:
            continue

        raw_val = form_data.get(col_name)
        if raw_val is None or raw_val == "":
            if col["nullable"]:
                val = None
            else:
                return False, f"Field '{col_name}' cannot be empty."
        else:
            dt = col["data_type"]
            try:
                if dt in ("int", "tinyint", "bigint"):
                    val = int(raw_val)
                elif dt in ("decimal", "float", "double"):
                    val = float(raw_val)
                elif dt == "tinyint" and col["col_type"].startswith("tinyint(1)"):
                    val = True if str(raw_val).lower() in ("true", "1", "on", "yes") else False
                else:
                    val = str(raw_val).strip()
            except ValueError:
                return False, f"Invalid numeric format for '{col_name}'."

        assignments.append(f"`{col_name}` = %s")
        values.append(val)

    if not assignments:
        return False, "No fields modified."

    sql = f"UPDATE `{table_name}` SET {', '.join(assignments)} WHERE `{pk_col}` = %s"
    values.append(record_id)

    try:
        execute_stmt(sql, tuple(values))
        return True, "Record updated successfully."
    except Exception as e:
        return False, translate_db_error(e)


def delete_row(table_name: str, record_id: Any) -> Tuple[bool, str]:
    """Delete a record from table_name using parameterized SQL."""
    schema = get_table_schema(table_name)
    pk_col = schema["primary_key"]
    sql = f"DELETE FROM `{table_name}` WHERE `{pk_col}` = %s"
    try:
        execute_stmt(sql, (record_id,))
        return True, "Record deleted successfully."
    except Exception as e:
        return False, translate_db_error(e)
