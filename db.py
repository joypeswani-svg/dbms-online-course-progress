import os
import mysql.connector
from dotenv import load_dotenv

load_dotenv()

DB_HOST = os.getenv("DB_HOST", "127.0.0.1")
DB_PORT = int(os.getenv("DB_PORT", "3306"))
DB_USER = os.getenv("DB_USER", "root")
DB_PASSWORD = os.getenv("DB_PASSWORD", "root")
DB_NAME = os.getenv("DB_NAME", "course_progress_db")


def get_db():
    """Return a raw connection from mysql-connector-python configured with dictionary cursors."""
    return mysql.connector.connect(
        host=DB_HOST,
        port=DB_PORT,
        user=DB_USER,
        password=DB_PASSWORD,
        database=DB_NAME,
        autocommit=False,
    )


def query_all(sql, params=None):
    """Execute raw parameterized SELECT and return all rows as dicts."""
    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute(sql, params or ())
        rows = cursor.fetchall()
        return rows
    finally:
        cursor.close()
        conn.close()


def query_one(sql, params=None):
    """Execute raw parameterized SELECT and return single row as dict or None."""
    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute(sql, params or ())
        row = cursor.fetchone()
        return row
    finally:
        cursor.close()
        conn.close()


def execute_stmt(sql, params=None, autocommit=True):
    """Execute raw parameterized INSERT/UPDATE/DELETE and return lastrowid and rowcount."""
    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute(sql, params or ())
        if autocommit:
            conn.commit()
        last_id = cursor.lastrowid
        affected = cursor.rowcount
        return {"last_id": last_id, "rowcount": affected}
    except Exception:
        conn.rollback()
        raise
    finally:
        cursor.close()
        conn.close()
