"""
Initialize the local SQLite database for Recon IA.
Ensures the database file and all required tables exist.
"""

import os
import sqlite3
from db import models

# ============================================================
# DATABASE PATHS
# ============================================================

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DB_PATH = os.path.join(PROJECT_ROOT, "data", "sessions.db")

# Lista derivada automáticamente del módulo models (mejor práctica)
REQUIRED_TABLE_NAMES = [
    stmt.split()[2]   # Extrae el nombre después de "CREATE TABLE IF NOT EXISTS X"
    for stmt in models.TABLES
]


# ============================================================
# CONNECTION FACTORY
# ============================================================

def get_connection():
    """
    Return a SQLite3 connection to the local database.
    Ensures that the database directory exists and foreign key constraints are enabled.
    """
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)

    conn = sqlite3.connect(DB_PATH, check_same_thread=False)

    # Enable foreign keys and WAL mode
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.execute("PRAGMA journal_mode = WAL;")

    return conn


# ============================================================
# DATABASE INITIALIZATION
# ============================================================

def init_database():
    """
    Creates all required tables from db/models.py.
    """
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
    """
    Ensures that the database file exists and contains all required tables.
    If tables are missing, they will be created.
    """
    # STEP 1: Si no existe el archivo → inicializar todo
    if not os.path.exists(DB_PATH):
        print("[init_db] Database file not found. Creating a new one...")
        init_database()
        return

    # STEP 2: Si existe archivo, validar tablas
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
        print("[init_db] Database OK — all tables already exist.")


# ============================================================
# CLI Entry Point
# ============================================================

if __name__ == "__main__":
    ensure_database_exists()
   