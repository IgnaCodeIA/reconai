"""
Operaciones CRUD (Create, Read, Update, Delete) sobre la base de datos local Recon IA.
Permite gestionar pacientes, ejercicios, sesiones y métricas.
"""

from db.init_db import get_connection


# ============================================================
# PACIENTES
# ============================================================

def create_patient(name, age=None, gender=None, notes=None):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO patients (name, age, gender, notes)
            VALUES (?, ?, ?, ?)
        """, (name, age, gender, notes))
        conn.commit()
        return cursor.lastrowid


def get_all_patients():
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, name, age, gender, notes, created_at FROM patients")
        return cursor.fetchall()


def get_patient_by_id(patient_id):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM patients WHERE id = ?", (patient_id,))
        return cursor.fetchone()


def update_patient(patient_id, name=None, age=None, gender=None, notes=None):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE patients
            SET name = COALESCE(?, name),
                age = COALESCE(?, age),
                gender = COALESCE(?, gender),
                notes = COALESCE(?, notes)
            WHERE id = ?
        """, (name, age, gender, notes, patient_id))
        conn.commit()


def delete_patient(patient_id):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM patients WHERE id = ?", (patient_id,))
        conn.commit()


# ============================================================
# EJERCICIOS
# ============================================================

def create_exercise(name, description=None):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT OR IGNORE INTO exercises (name, description)
            VALUES (?, ?)
        """, (name, description))
        conn.commit()
        return cursor.lastrowid


def get_all_exercises():
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, name, description FROM exercises")
        return cursor.fetchall()


# ============================================================
# SESIONES
# ============================================================

def create_session(patient_id, exercise_id=None, csv_path=None, video_path=None):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO sessions (patient_id, exercise_id, csv_path, video_path)
            VALUES (?, ?, ?, ?)
        """, (patient_id, exercise_id, csv_path, video_path))
        conn.commit()
        return cursor.lastrowid


def get_sessions_by_patient(patient_id):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT s.id, s.timestamp, e.name AS exercise_name, s.csv_path, s.video_path
            FROM sessions s
            LEFT JOIN exercises e ON s.exercise_id = e.id
            WHERE s.patient_id = ?
            ORDER BY s.timestamp DESC
        """, (patient_id,))
        return cursor.fetchall()


# ============================================================
# MÉTRICAS
# ============================================================

def add_metric(session_id, metric_name, metric_value):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO metrics (session_id, metric_name, metric_value)
            VALUES (?, ?, ?)
        """, (session_id, metric_name, metric_value))
        conn.commit()


def get_metrics_by_session(session_id):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT metric_name, metric_value
            FROM metrics
            WHERE session_id = ?
        """, (session_id,))
        return cursor.fetchall()


# ============================================================
# UTILIDAD GENERAL
# ============================================================

def get_table_counts():
    """Devuelve un resumen de la cantidad de registros por tabla."""
    with get_connection() as conn:
        cursor = conn.cursor()
        tables = ["patients", "exercises", "sessions", "metrics"]
        return {t: cursor.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0] for t in tables}
