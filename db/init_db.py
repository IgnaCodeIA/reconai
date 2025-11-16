"""
Initialize the local SQLite database for Recon IA.
Creates the database file and all required tables if they do not already exist.
"""

import os
import sqlite3
from db import models

# ============================================================
# DATABASE CONFIGURATION
# ============================================================

# Ruta ABSOLUTA, compartida por UI y worker WebRTC
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DB_PATH = os.path.join(PROJECT_ROOT, "data", "sessions.db")


def get_connection():
    """
    Return a SQLite3 connection to the local database.
    Ensures that the database directory exists and foreign key constraints are enabled.
    """
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    # check_same_thread=False para hilos (webrtc) y WAL para concurrencia
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.execute("PRAGMA journal_mode = WAL;")
    return conn


def init_database():
    """
    Initialize the Recon IA local database.
    Creates all tables defined in db/models.py if they do not exist.
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


if __name__ == "__main__":
    init_database()