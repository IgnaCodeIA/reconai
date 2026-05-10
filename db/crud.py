import sqlite3
from typing import List, Dict, Any, Tuple
from db.init_db import get_connection
from core.logger import get_logger

log = get_logger("db.crud")


def create_patient(
    name: str,
    dni: str | None = None,
    age: int | None = None,
    gender: str | None = None,
    notes: str | None = None
) -> int:
    """Insert a new patient row and return its id. Raises ValueError on bad gender or duplicate DNI."""
    log.debug(
        "create_patient called with name=%s, dni=%s, age=%s, gender=%s",
        name, dni, age, gender
    )
    if gender and gender not in ("M", "F", "Other"):
        raise ValueError(f"Invalid gender: {gender}. Use 'M', 'F' or 'Other'")

    with get_connection() as conn:
        cur = conn.cursor()

        if dni:
            cur.execute("SELECT id FROM patients WHERE dni = ?", (dni,))
            if cur.fetchone():
                raise ValueError(f"A patient with DNI {dni} already exists")

        cur.execute(
            """
            INSERT INTO patients (name, dni, age, gender, notes)
            VALUES (?, ?, ?, ?, ?)
            """,
            (name, dni, age, gender, notes)
        )
        conn.commit()
        return cur.lastrowid


def get_all_patients() -> List[Tuple]:
    """Return every patient row, ordered by name."""
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            "SELECT id, name, dni, age, gender, notes, created_at FROM patients ORDER BY name"
        )
        return cur.fetchall()


def get_patient_by_id(patient_id: int) -> Tuple | None:
    """Return the patient row with the given id, or None if not found."""
    log.debug("get_patient_by_id called with patient_id=%s", patient_id)
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            "SELECT id, name, dni, age, gender, notes, created_at FROM patients WHERE id = ?",
            (patient_id,)
        )
        return cur.fetchone()


def update_patient(
    patient_id: int,
    name: str | None = None,
    dni: str | None = None,
    age: int | None = None,
    gender: str | None = None,
    notes: str | None = None
) -> bool:
    """Update the provided fields for a patient. Returns True if a row was modified."""
    log.debug(
        "update_patient called with patient_id=%s, name=%s, dni=%s, age=%s, gender=%s",
        patient_id, name, dni, age, gender
    )
    if gender and gender not in ("M", "F", "Other"):
        raise ValueError(f"Invalid gender: {gender}")

    with get_connection() as conn:
        cur = conn.cursor()

        fields = []
        values = []

        if name is not None:
            fields.append("name = ?")
            values.append(name)
        if dni is not None:
            fields.append("dni = ?")
            values.append(dni)
        if age is not None:
            fields.append("age = ?")
            values.append(age)
        if gender is not None:
            fields.append("gender = ?")
            values.append(gender)
        if notes is not None:
            fields.append("notes = ?")
            values.append(notes)

        if not fields:
            return False

        values.append(patient_id)
        query = f"UPDATE patients SET {', '.join(fields)} WHERE id = ?"

        cur.execute(query, values)
        conn.commit()
        return cur.rowcount > 0


def delete_patient(patient_id: int, cascade: bool = True) -> bool:
    """Delete a patient. If cascade is True, also delete the patient's sessions and related rows."""
    log.debug("delete_patient called with patient_id=%s, cascade=%s", patient_id, cascade)
    with get_connection() as conn:
        cur = conn.cursor()

        if cascade:
            cur.execute("SELECT id FROM sessions WHERE patient_id = ?", (patient_id,))
            session_ids = [row[0] for row in cur.fetchall()]

            for sid in session_ids:
                cur.execute("DELETE FROM movement_data WHERE session_id = ?", (sid,))
                cur.execute("DELETE FROM metrics WHERE session_id = ?", (sid,))

            cur.execute("DELETE FROM sessions WHERE patient_id = ?", (patient_id,))

        cur.execute("DELETE FROM patients WHERE id = ?", (patient_id,))
        conn.commit()
        return cur.rowcount > 0


def create_exercise(name: str, description: str | None = None) -> int:
    """Insert a new exercise (or return the id of the existing one with the same name)."""
    log.debug("create_exercise called with name=%s", name)
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            "INSERT OR IGNORE INTO exercises (name, description) VALUES (?, ?)",
            (name, description)
        )
        if cur.lastrowid:
            conn.commit()
            return cur.lastrowid

        cur.execute("SELECT id FROM exercises WHERE name = ?", (name,))
        row = cur.fetchone()
        return row[0] if row else 0


def get_all_exercises() -> List[Tuple]:
    """Return every exercise row, ordered by name."""
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("SELECT id, name, description FROM exercises ORDER BY name")
        return cur.fetchall()


def update_exercise(exercise_id: int, name: str | None = None, description: str | None = None) -> bool:
    """Update the provided fields for an exercise. Returns True if a row was modified."""
    log.debug(
        "update_exercise called with exercise_id=%s, name=%s",
        exercise_id, name
    )
    with get_connection() as conn:
        cur = conn.cursor()

        fields = []
        values = []

        if name is not None:
            fields.append("name = ?")
            values.append(name)
        if description is not None:
            fields.append("description = ?")
            values.append(description)

        if not fields:
            return False

        values.append(exercise_id)
        query = f"UPDATE exercises SET {', '.join(fields)} WHERE id = ?"

        cur.execute(query, values)
        conn.commit()
        return cur.rowcount > 0


def delete_exercise(exercise_id: int, cascade: bool = True) -> bool:
    """Delete an exercise. If cascade is True, also delete sessions referencing it and their data."""
    log.debug("delete_exercise called with exercise_id=%s, cascade=%s", exercise_id, cascade)
    with get_connection() as conn:
        cur = conn.cursor()

        if cascade:
            cur.execute("SELECT id FROM sessions WHERE exercise_id = ?", (exercise_id,))
            session_ids = [row[0] for row in cur.fetchall()]

            for sid in session_ids:
                cur.execute("DELETE FROM movement_data WHERE session_id = ?", (sid,))
                cur.execute("DELETE FROM metrics WHERE session_id = ?", (sid,))

            cur.execute("DELETE FROM sessions WHERE exercise_id = ?", (exercise_id,))

        cur.execute("DELETE FROM exercises WHERE id = ?", (exercise_id,))
        conn.commit()
        return cur.rowcount > 0


def create_session(
    patient_id: int | None = None,
    exercise_id: int | None = None,
    video_path_raw: str | None = None,
    video_path_mediapipe: str | None = None,
    video_path_legacy: str | None = None,
    notes: str | None = None
) -> int:
    """Create a new session row linking a patient, exercise, and video output paths."""
    log.debug(
        "create_session called with patient_id=%s, exercise_id=%s, raw=%s, mp=%s, legacy=%s",
        patient_id, exercise_id, video_path_raw, video_path_mediapipe, video_path_legacy
    )
    with get_connection() as conn:
        cur = conn.cursor()

        video_path = video_path_legacy or video_path_mediapipe or video_path_raw

        cur.execute(
            """
            INSERT INTO sessions (
                patient_id, exercise_id,
                video_path_raw, video_path_mediapipe, video_path_legacy,
                video_path, notes
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (patient_id, exercise_id,
             video_path_raw, video_path_mediapipe, video_path_legacy,
             video_path, notes)
        )
        conn.commit()
        return cur.lastrowid


def get_all_sessions() -> List[Dict[str, Any]]:
    """Return every session, joined with patient and exercise names, newest first."""
    with get_connection() as conn:
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute(
            """
            SELECT
                s.id,
                s.timestamp AS datetime,
                s.video_path,
                s.video_path_raw,
                s.video_path_mediapipe,
                s.video_path_legacy,
                s.notes,
                p.name AS patient_name,
                e.name AS exercise_name
            FROM sessions s
            LEFT JOIN patients p ON s.patient_id = p.id
            LEFT JOIN exercises e ON s.exercise_id = e.id
            ORDER BY s.timestamp DESC
            """
        )
        return [dict(row) for row in cur.fetchall()]


def get_sessions_by_patient(patient_id: int) -> List[Dict[str, Any]]:
    """Return all sessions for the given patient, newest first."""
    log.debug("get_sessions_by_patient called with patient_id=%s", patient_id)
    with get_connection() as conn:
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute(
            """
            SELECT
                s.id,
                s.timestamp AS datetime,
                s.video_path,
                s.video_path_raw,
                s.video_path_mediapipe,
                s.video_path_legacy,
                s.notes,
                e.name AS exercise_name
            FROM sessions s
            LEFT JOIN exercises e ON s.exercise_id = e.id
            WHERE s.patient_id = ?
            ORDER BY s.timestamp DESC
            """,
            (patient_id,)
        )
        return [dict(row) for row in cur.fetchall()]


def delete_session(session_id: int) -> bool:
    """Delete a session along with its movement_data and metrics rows."""
    log.debug("delete_session called with session_id=%s", session_id)
    with get_connection() as conn:
        cur = conn.cursor()

        cur.execute("DELETE FROM movement_data WHERE session_id = ?", (session_id,))
        cur.execute("DELETE FROM metrics WHERE session_id = ?", (session_id,))
        cur.execute("DELETE FROM sessions WHERE id = ?", (session_id,))

        conn.commit()
        return cur.rowcount > 0


def add_movement_data(session_id: int, data: Dict[str, Any]) -> None:
    """Insert one per-frame movement_data row built from the given dict."""
    if not data:
        return

    data["session_id"] = session_id

    columns = list(data.keys())
    placeholders = ["?" for _ in columns]
    values = [data[col] for col in columns]

    query = f"""
        INSERT INTO movement_data ({', '.join(columns)})
        VALUES ({', '.join(placeholders)})
    """

    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute(query, values)
        conn.commit()


def get_movement_data_by_session(session_id: int) -> List[Dict[str, Any]]:
    """Return all movement_data rows for a session, ordered by frame index."""
    log.debug("get_movement_data_by_session called with session_id=%s", session_id)
    with get_connection() as conn:
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute(
            "SELECT * FROM movement_data WHERE session_id = ? ORDER BY frame",
            (session_id,)
        )
        return [dict(row) for row in cur.fetchall()]


def add_metric(
    session_id: int,
    metric_name: str,
    metric_value: float,
    unit: str | None = None
) -> None:
    """Insert one metric row associated with a session."""
    log.debug(
        "add_metric called with session_id=%s, metric_name=%s, metric_value=%s, unit=%s",
        session_id, metric_name, metric_value, unit
    )
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO metrics (session_id, metric_name, metric_value, unit)
            VALUES (?, ?, ?, ?)
            """,
            (session_id, metric_name, metric_value, unit)
        )
        conn.commit()


def get_metrics_by_session(session_id: int) -> List[Tuple[str, float, str]]:
    """Return all metric rows for a session, ordered by metric_name."""
    log.debug("get_metrics_by_session called with session_id=%s", session_id)
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            "SELECT metric_name, metric_value, unit FROM metrics WHERE session_id = ? ORDER BY metric_name",
            (session_id,)
        )
        return cur.fetchall()


def get_table_counts() -> Dict[str, int]:
    """Return a dict of {table_name: row_count} for the main DB tables."""
    with get_connection() as conn:
        cur = conn.cursor()

        counts = {}
        for table in ["patients", "exercises", "sessions", "metrics"]:
            cur.execute(f"SELECT COUNT(*) FROM {table}")
            counts[table] = cur.fetchone()[0]

        return counts


from db import feedback_crud

create_feedback = feedback_crud.create_feedback
get_all_feedback = feedback_crud.get_all_feedback
get_feedback_by_id = feedback_crud.get_feedback_by_id
update_feedback_status = feedback_crud.update_feedback_status
delete_feedback = feedback_crud.delete_feedback
get_feedback_stats = feedback_crud.get_feedback_stats
