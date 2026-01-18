"""
Initialize the local SQLite database for Recon IA.
Ensures the database file and all required tables exist.

CRÍTICO: Usa path_manager para ubicar la BD en AppData (persiste entre actualizaciones).
"""

import sqlite3
from pathlib import Path

# Importar el gestor de rutas
from core.path_manager import get_db_path, get_database_dir

from db import models

# ============================================================
# DATABASE PATH (usando path_manager)
# ============================================================

# Ruta de la base de datos (persistente en AppData)
DB_PATH = get_db_path()

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
    
    IMPORTANTE: La BD se crea en AppData usando path_manager, no en el directorio
    del ejecutable.
    """
    # Asegurar que el directorio de la BD existe
    db_dir = get_database_dir()
    db_dir.mkdir(parents=True, exist_ok=True)

    # Convertir Path a string para compatibilidad con sqlite3
    conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)

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
    if not DB_PATH.exists():
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
    print("=" * 60)
    print("PRUEBA DE INICIALIZACIÓN DE BASE DE DATOS")
    print("=" * 60)
    print(f"\n📄 Ruta de la BD: {DB_PATH}")
    print(f"📁 Directorio de BD: {get_database_dir()}")
    
    ensure_database_exists()
    
    # Verificar que se creó
    if DB_PATH.exists():
        print(f"\n✅ Base de datos creada exitosamente")
        print(f"   Tamaño: {DB_PATH.stat().st_size} bytes")
        
        # Listar tablas
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = [row[0] for row in cursor.fetchall()]
        conn.close()
        
        print(f"   Tablas creadas: {', '.join(tables)}")
    else:
        print("\n❌ Error: La base de datos no se creó")
    
    print("=" * 60)