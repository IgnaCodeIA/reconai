import sqlite3
from pathlib import Path

from core.path_manager import get_db_path, get_database_dir
from db import models

DB_PATH = get_db_path()

def _extract_table_name(stmt):
    parts = stmt.split()
    try:
        idx = parts.index("TABLE")
        for i in range(idx + 1, len(parts)):
            if parts[i] not in ("IF", "NOT", "EXISTS"):
                return parts[i].replace("(", "").strip()
    except (ValueError, IndexError):
        pass
    return None

REQUIRED_TABLE_NAMES = [
    name for name in (_extract_table_name(stmt) for stmt in models.TABLES) if name
]


def get_connection():
    db_dir = get_database_dir()
    db_dir.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)

    conn.execute("PRAGMA foreign_keys = ON;")
    conn.execute("PRAGMA journal_mode = WAL;")

    return conn


def init_database():
    conn = get_connection()
    try:
        cursor = conn.cursor()
        for table_sql in models.TABLES:
            cursor.execute(table_sql)
        conn.commit()
        print(f"[init_db] Database successfully initialized at: {DB_PATH}")
    except sqlite3.Error as e:
        print(f"[init_db] SQLite error during initialization: {e}")
        raise
    finally:
        conn.close()


def ensure_database_exists():
    if not DB_PATH.exists():
        print(f"[init_db] Database file not found. Creating at: {DB_PATH}")
        init_database()
        return

    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        existing_table_names = {row[0] for row in cursor.fetchall()}

    finally:
        conn.close()

    missing = [t for t in REQUIRED_TABLE_NAMES if t not in existing_table_names]

    if missing:
        print(f"[init_db] Missing tables detected: {missing}")
        print("[init_db] Creating missing tables...")
        init_database()
    else:
        print(f"[init_db] Database OK at: {DB_PATH}")