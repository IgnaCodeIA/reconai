"""
Initialize the local SQLite database for Recon IA.
Ensures the database file and all required tables exist.

CRÍTICO: En ejecutable, la BD debe estar fuera de _MEIPASS para persistir.
"""

import os
import sys
import sqlite3
from db import models

# ============================================================
# DATABASE PATHS (PyInstaller compatible)
# ============================================================

def get_data_directory():
    """
    Obtiene el directorio de datos persistente.
    
    En ejecutable: usa directorio del .exe (no _MEIPASS)
    En desarrollo: usa directorio del proyecto
    """
    if getattr(sys, 'frozen', False):
        # Ejecutable: directorio donde está el .exe
        # os.path.dirname(sys.executable) da la carpeta del .exe
        exe_dir = os.path.dirname(sys.executable)
        data_dir = os.path.join(exe_dir, "data")
    else:
        # Desarrollo: carpeta data/ en raíz del proyecto
        project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        data_dir = os.path.join(project_root, "data")
    
    return data_dir


# Ruta de la base de datos (persistente)
DATA_DIR = get_data_directory()
DB_PATH = os.path.join(DATA_DIR, "sessions.db")

# Lista derivada automáticamente del módulo models
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
    os.makedirs(DATA_DIR, exist_ok=True)

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
        print(f"[init_db] Database file not found. Creating at: {DB_PATH}")
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
        print(f"[init_db] Database OK at: {DB_PATH}")


# ============================================================
# CLI Entry Point
# ============================================================

if __name__ == "__main__":
    ensure_database_exists()