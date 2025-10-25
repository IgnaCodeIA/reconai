"""
Inicializa la base de datos SQLite local de Recon IA.
Crea el archivo y las tablas necesarias si no existen.
"""

import os
import sqlite3
from db import models


DB_PATH = os.path.join("data", "sessions.db")


def get_connection():
    """
    Devuelve una conexión SQLite a la base de datos local.
    Crea la carpeta y el archivo si no existen.
    """
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON;")  # Habilita claves foráneas
    return conn


def init_database():
    """
    Crea todas las tablas definidas en db/models.py.
    Si la base de datos ya existe, se asegura de que las tablas estén disponibles.
    """
    conn = get_connection()
    cursor = conn.cursor()

    for table_sql in models.TABLES:
        cursor.execute(table_sql)

    conn.commit()
    conn.close()
    print(f"[init_db] Base de datos inicializada en: {DB_PATH}")


if __name__ == "__main__":
    init_database()
