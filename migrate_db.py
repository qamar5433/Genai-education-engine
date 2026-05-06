"""
migrate_db.py
-------------
One-time migration for existing quizgenius.db.
Adds new OTP/auth columns to the users table if missing.

Run ONCE from the project root:
  python migrate_db.py

Safe to run multiple times - uses ALTER TABLE only when column is missing.
"""

import sqlite3
import os

DB_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "backend", "quizgenius.db"
)

# (column_name, sql_type)
NEW_COLUMNS = [
    ("otp_resend_at",        "DATETIME"),
    ("reset_otp",            "VARCHAR(10)"),
    ("reset_otp_expires_at", "DATETIME"),
]

def column_exists(cursor, table, column):
    cursor.execute(f"PRAGMA table_info({table})")
    return column in [row[1] for row in cursor.fetchall()]

def run_migration():
    if not os.path.exists(DB_PATH):
        print("[ERROR] Database not found at:", DB_PATH)
        print("        Start the server once so SQLAlchemy creates the DB, then re-run.")
        return

    conn   = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    added  = []

    for col_name, col_type in NEW_COLUMNS:
        if column_exists(cursor, "users", col_name):
            print(f"[SKIP]  Column '{col_name}' already exists.")
        else:
            cursor.execute(f"ALTER TABLE users ADD COLUMN {col_name} {col_type}")
            added.append(col_name)
            print(f"[ADD]   Column '{col_name}' ({col_type}) added.")

    conn.commit()
    conn.close()

    if added:
        print(f"\n[DONE]  Migration complete. Added: {', '.join(added)}")
    else:
        print("\n[DONE]  Database already up to date. No changes needed.")

if __name__ == "__main__":
    run_migration()
