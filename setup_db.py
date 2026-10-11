#!/usr/bin/env python3
"""
Database Setup Script for Project 34: Online Course Learning Progress Management System.
Executes schema.sql, procedures.sql, views.sql, and seed.sql sequentially.
"""

import os
import re
import sys
import pymysql
from dotenv import load_dotenv

load_dotenv()

DB_HOST = os.getenv("DB_HOST", "127.0.0.1")
DB_PORT = int(os.getenv("DB_PORT", "3306"))
DB_USER = os.getenv("DB_USER", "root")
DB_PASSWORD = os.getenv("DB_PASSWORD", "root")
DB_NAME = os.getenv("DB_NAME", "course_progress_db")


def execute_sql_file(cursor, file_path):
    print(f"\n---> Executing: {file_path}")
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    # Parse and execute handling DELIMITER $$ properly
    delimiter = ";"
    buffer = []
    
    lines = content.splitlines()
    for line in lines:
        stripped = line.strip()
        
        # Check for DELIMITER change
        if stripped.upper().startswith("DELIMITER"):
            parts = stripped.split()
            if len(parts) >= 2:
                delimiter = parts[1]
            continue
        
        # Skip pure comment lines when buffer is empty
        if not buffer and (stripped.startswith("--") or stripped.startswith("/*") or not stripped):
            continue
            
        buffer.append(line)
        
        # Check if line ends with current delimiter
        if stripped.endswith(delimiter):
            stmt = "\n".join(buffer)
            # Remove trailing delimiter
            stmt = stmt[: -len(delimiter)].strip()
            buffer = []
            if stmt:
                try:
                    cursor.execute(stmt)
                except Exception as e:
                    print(f"Error executing statement:\n{stmt[:200]}...\nDetails: {e}")
                    raise

    if buffer:
        stmt = "\n".join(buffer).strip()
        if stmt:
            cursor.execute(stmt)

    print(f"✓ Completed: {file_path}")


def main():
    print("=" * 60)
    print("Initializing Database Setup (MySQL 8.0+)")
    print(f"Target: {DB_USER}@{DB_HOST}:{DB_PORT}/{DB_NAME}")
    print("=" * 60)

    # First connect without specifying database to ensure DB exists
    conn = pymysql.connect(
        host=DB_HOST,
        port=DB_PORT,
        user=DB_USER,
        password=DB_PASSWORD,
        charset="utf8mb4",
        autocommit=True
    )
    cursor = conn.cursor()
    cursor.execute(f"CREATE DATABASE IF NOT EXISTS `{DB_NAME}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;")
    cursor.execute(f"USE `{DB_NAME}`;")
    print(f"✓ Database `{DB_NAME}` confirmed ready.")

    sql_files = [
        "sql/schema.sql",
        "sql/procedures.sql",
        "sql/views.sql",
        "sql/seed.sql"
    ]

    for fpath in sql_files:
        if not os.path.exists(fpath):
            print(f"ERROR: File not found: {fpath}")
            sys.exit(1)
        execute_sql_file(cursor, fpath)

    cursor.close()
    conn.close()
    print("\n" + "=" * 60)
    print("All SQL scripts executed successfully with ZERO errors!")
    print("=" * 60)


if __name__ == "__main__":
    main()
