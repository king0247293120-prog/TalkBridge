
import sqlite3
from pathlib import Path

DB_PATH = Path("talkbridge.db")

if not DB_PATH.exists():
    raise FileNotFoundError(
        f"Database not found: {DB_PATH.resolve()}"
    )

connection = sqlite3.connect(DB_PATH)
cursor = connection.cursor()

try:
    cursor.execute("PRAGMA table_info(translation_entries)")
    existing_columns = {
        row[1] for row in cursor.fetchall()
    }

    if not existing_columns:
        raise RuntimeError(
            "translation_entries table does not exist."
        )

    if "provider" not in existing_columns:
        cursor.execute("""
            ALTER TABLE translation_entries
            ADD COLUMN provider VARCHAR(100)
            DEFAULT 'open_source_model'
        """)
        print("Added provider column.")

    if "updated_at" not in existing_columns:
        cursor.execute("""
            ALTER TABLE translation_entries
            ADD COLUMN updated_at DATETIME
        """)
        cursor.execute("""
            UPDATE translation_entries
            SET updated_at = CURRENT_TIMESTAMP
            WHERE updated_at IS NULL
        """)
        print("Added and populated updated_at column.")

    if "status" not in existing_columns:
        cursor.execute("""
            ALTER TABLE translation_entries
            ADD COLUMN status VARCHAR(20)
            DEFAULT 'pending'
        """)
        print("Added status column.")

    connection.commit()
    print("Database migration completed successfully.")

except Exception:
    connection.rollback()
    raise

finally:
    connection.close()
