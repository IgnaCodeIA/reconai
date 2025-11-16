# db/crud.py
"""
CRUD operations (Create, Read, Update, Delete) for the local Recon IA database.

Provides helper functions to manage patients, exercises, sessions,
movement data, and metrics with automatic connection management.
"""

import sqlite3
from db.init_db import get_connection
from core.logger import get_logger

log = get_logger("db.crud")

# ============================================================
# PATIENTS
# ============================================================

def create_patient(name, dni=None, age=None, gender=None, notes=None):
    """Crea un nuevo paciente, validando que el DNI no exista previamente."""
    with get_connection() as conn:
        cursor = conn.cursor()

        if gender not in ["M", "F", "Other"]:
            gender = "Other"
        try:
            age = int(age) if age is not None else None
        except ValueError:
            age = None

        # Evitar duplicados por DNI
        if dni:
            cursor.execute("SELECT id FROM patients WHERE dni = ?", (dni,))
            if cursor.fetchone():
                raise ValueError("Ya existe un paciente con ese DNI.")

        cursor.execute("""
            INSERT INTO patients (name, dni, age, gender, notes)
            VALUES (?, ?, ?, ?, ?)
        """, (name, dni, age, gender, notes))
        conn.commit()
        pid = cursor.lastrowid
        log.info(f"create_patient OK: id={pid}")
        return pid


def get_all_patients():
    """Devuelve todos los pacientes registrados."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, name, dni, age, gender, notes, created_at
            FROM patients
            ORDER BY created_at DESC
        """)
        return cursor.fetchall()


def get_patient_by_id(patient_id):
    """Obtiene un paciente por su ID."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM patients WHERE id = ?", (patient_id,))
        return cursor.fetchone()


def update_patient(patient_id, name=None, dni=None, age=None, gender=None, notes=None):
    """Actualiza un paciente existente con validaciones básicas."""
    with get_connection() as conn:
        cursor = conn.cursor()

        if gender not in ["M", "F", "Other"]:
            gender = "Other"
        try:
            age = int(age) if age is not None else None
        except ValueError:
            age = None

        cursor.execute("""
            UPDATE patients
            SET name = COALESCE(?, name),
                dni = COALESCE(?, dni),
                age = COALESCE(?, age),
                gender = COALESCE(?, gender),
                notes = COALESCE(?, notes)
            WHERE id = ?
        """, (name, dni, age, gender, notes, patient_id))
        conn.commit()
        ok = cursor.rowcount > 0
        log.info(f"update_patient id={patient_id} -> {'OK' if ok else 'NO-OP'}")
        return ok


def delete_patient(patient_id, cascade=True):
    """Elimina un paciente (y opcionalmente sus sesiones, métricas y movimiento)."""
    with get_connection() as conn:
        cursor = conn.cursor()
        try:
            if cascade:
                cursor.execute("""
                    DELETE FROM metrics
                    WHERE session_id IN (SELECT id FROM sessions WHERE patient_id = ?)
                """, (patient_id,))
                cursor.execute("""
                    DELETE FROM movement_data
                    WHERE session_id IN (SELECT id FROM sessions WHERE patient_id = ?)
                """, (patient_id,))
                cursor.execute("DELETE FROM sessions WHERE patient_id = ?", (patient_id,))

            cursor.execute("DELETE FROM patients WHERE id = ?", (patient_id,))
            conn.commit()
            ok = cursor.rowcount > 0
            log.info(f"delete_patient id={patient_id}, cascade={cascade} -> {'OK' if ok else 'NOT FOUND'}")
            return ok

        except sqlite3.Error:
            log.exception(f"delete_patient FAILED id={patient_id}")
            conn.rollback()
            return False


# ============================================================
# EXERCISES
# ============================================================

def create_exercise(name, description=None):
    """Crea un nuevo ejercicio."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT OR IGNORE INTO exercises (name, description)
            VALUES (?, ?)
        """, (name, description))
        conn.commit()
        eid = cursor.lastrowid
        log.info(f"create_exercise OK: id={eid}")
        return eid


def get_all_exercises():
    """Devuelve todos los ejercicios registrados."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, name, description FROM exercises")
        return cursor.fetchall()


def update_exercise(exercise_id, name=None, description=None):
    """Actualiza un ejercicio existente."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE exercises
            SET name = COALESCE(?, name),
                description = COALESCE(?, description)
            WHERE id = ?
        """, (name, description, exercise_id))
        conn.commit()
        ok = cursor.rowcount > 0
        log.info(f"update_exercise id={exercise_id} -> {'OK' if ok else 'NO-OP'}")
        return ok


def delete_exercise(exercise_id, cascade=True):
    """Elimina un ejercicio y opcionalmente sus sesiones y métricas asociadas."""
    with get_connection() as conn:
        cursor = conn.cursor()
        try:
            if cascade:
                cursor.execute("""
                    DELETE FROM metrics
                    WHERE session_id IN (SELECT id FROM sessions WHERE exercise_id = ?)
                """, (exercise_id,))
                cursor.execute("""
                    DELETE FROM movement_data
                    WHERE session_id IN (SELECT id FROM sessions WHERE exercise_id = ?)
                """, (exercise_id,))
                cursor.execute("DELETE FROM sessions WHERE exercise_id = ?", (exercise_id,))

            cursor.execute("DELETE FROM exercises WHERE id = ?", (exercise_id,))
            conn.commit()
            ok = cursor.rowcount > 0
            log.info(f"delete_exercise id={exercise_id}, cascade={cascade} -> {'OK' if ok else 'NOT FOUND'}")
            return ok

        except sqlite3.Error:
            log.exception(f"delete_exercise FAILED id={exercise_id}")
            conn.rollback()
            return False


# ============================================================
# SESSIONS
# ============================================================

def create_session(patient_id, exercise_id=None, video_path=None, notes=None):
    """Crea una nueva sesión de análisis."""
    with get_connection() as conn:
        cursor = conn.cursor()
        try:
            cursor.execute("""
                INSERT INTO sessions (patient_id, exercise_id, video_path, notes)
                VALUES (?, ?, ?, ?)
            """, (patient_id, exercise_id, video_path, notes))
            conn.commit()
            sid = cursor.lastrowid
            log.info(f"create_session OK: session_id={sid}")
            return sid
        except Exception:
            log.exception("create_session FAILED")
            conn.rollback()
            raise


def get_all_sessions():
    """Devuelve todas las sesiones registradas."""
    with get_connection() as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("""
            SELECT 
                s.id,
                s.timestamp AS datetime,
                p.name AS patient_name,
                e.name AS exercise_name,
                s.video_path,
                s.notes
            FROM sessions s
            LEFT JOIN patients p ON s.patient_id = p.id
            LEFT JOIN exercises e ON s.exercise_id = e.id
            ORDER BY s.timestamp DESC
        """)
        return [dict(row) for row in cursor.fetchall()]


def get_sessions_by_patient(patient_id):
    """Devuelve todas las sesiones de un paciente."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT s.id, s.timestamp, e.name AS exercise_name, s.video_path, s.notes
            FROM sessions s
            LEFT JOIN exercises e ON s.exercise_id = e.id
            WHERE s.patient_id = ?
            ORDER BY s.timestamp DESC
        """, (patient_id,))
        return cursor.fetchall()


def delete_session(session_id):
    """Elimina una sesión y todos sus datos asociados (métricas, movimiento, etc.)."""
    with get_connection() as conn:
        cursor = conn.cursor()
        try:
            cursor.execute("DELETE FROM metrics WHERE session_id = ?", (session_id,))
            cursor.execute("DELETE FROM movement_data WHERE session_id = ?", (session_id,))
            cursor.execute("DELETE FROM sessions WHERE id = ?", (session_id,))
            deleted_sessions = cursor.rowcount
            conn.commit()
            ok = deleted_sessions > 0
            log.info(f"delete_session id={session_id} -> {'OK' if ok else 'NOT FOUND'}")
            return ok
        except sqlite3.Error:
            log.exception(f"delete_session FAILED id={session_id}")
            conn.rollback()
            return False


# ============================================================
# MOVEMENT DATA
# ============================================================

def add_movement_data(session_id, data: dict):
    """Guarda un frame de datos de movimiento."""
    if not data:
        log.warning(f"add_movement_data: empty payload for session_id={session_id}")
        return

    columns = ["session_id"] + list(data.keys())
    placeholders = ", ".join("?" * len(columns))
    values = [session_id] + list(data.values())

    with get_connection() as conn:
        cursor = conn.cursor()
        try:
            cursor.execute(f"""
                INSERT INTO movement_data ({", ".join(columns)})
                VALUES ({placeholders})
            """, values)
            conn.commit()
        except Exception:
            log.exception(f"add_movement_data FAILED (session={session_id})")
            conn.rollback()
            raise


def get_movement_data_by_session(session_id):
    """Obtiene todos los frames de movimiento de una sesión."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM movement_data
            WHERE session_id = ?
            ORDER BY frame ASC
        """, (session_id,))
        return cursor.fetchall()


# ============================================================
# METRICS
# ============================================================

def add_metric(session_id, metric_name, metric_value, unit=None):
    """
    Agrega una métrica a una sesión (con conversión robusta).
    """
    mv = None
    if metric_value is not None:
        try:
            mv = float(metric_value)
        except (TypeError, ValueError):
            mv = None

    with get_connection() as conn:
        cursor = conn.cursor()
        try:
            cursor.execute("""
                INSERT INTO metrics (session_id, metric_name, metric_value, unit)
                VALUES (?, ?, ?, ?)
            """, (session_id, metric_name, mv, unit))
            conn.commit()
        except Exception:
            log.exception(f"add_metric FAILED: sid={session_id}, name={metric_name}")
            conn.rollback()
            raise


def get_metrics_by_session(session_id):
    """Devuelve las métricas asociadas a una sesión."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT metric_name, metric_value, unit
            FROM metrics
            WHERE session_id = ?
        """, (session_id,))
        return cursor.fetchall()


# ============================================================
# UTILITIES
# ============================================================

def get_table_counts():
    """Devuelve el número de registros en cada tabla principal."""
    tables = ["patients", "exercises", "sessions", "movement_data", "metrics"]
    with get_connection() as conn:
        cursor = conn.cursor()
        return {
            t: cursor.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
            for t in tables
        }