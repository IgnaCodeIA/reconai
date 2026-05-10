from __future__ import annotations

import sqlite3
from typing import Any

from db.init_db import get_connection
from core.logger import get_logger

log = get_logger("ai.query_engine")


def _fetchall_as_dicts(cur: sqlite3.Cursor) -> list[dict[str, Any]]:
    columns = [desc[0] for desc in cur.description]
    return [dict(zip(columns, row)) for row in cur.fetchall()]


def _safe_execute(
    query: str,
    params: tuple = (),
    *,
    label: str = "query",
) -> list[dict[str, Any]]:
    try:
        with get_connection() as conn:
            conn.row_factory = sqlite3.Row
            cur = conn.cursor()
            cur.execute(query, params)
            columns = [desc[0] for desc in cur.description]
            return [dict(zip(columns, row)) for row in cur.fetchall()]
    except sqlite3.Error as exc:
        log.error("[query_engine] Error in '%s': %s", label, exc)
        return []


def get_patients_list() -> list[dict[str, Any]]:
    """Return all patients with their basic fields."""
    return _safe_execute(
        """
        SELECT id, name, dni, age, gender, notes, created_at
        FROM patients
        ORDER BY name
        """,
        label="get_patients_list",
    )


def get_patient_by_name(name: str) -> list[dict[str, Any]]:
    """Search patients whose name contains the given fragment (case-insensitive)."""
    log.debug("get_patient_by_name called with name=%s", name)
    return _safe_execute(
        """
        SELECT id, name, dni, age, gender, notes, created_at
        FROM patients
        WHERE LOWER(name) LIKE LOWER(?)
        ORDER BY name
        """,
        (f"%{name}%",),
        label="get_patient_by_name",
    )


def get_patient_sessions(patient_id: int) -> list[dict[str, Any]]:
    """Return all sessions for a patient with the exercise name and metric count per session."""
    log.debug("get_patient_sessions called with patient_id=%s", patient_id)
    return _safe_execute(
        """
        SELECT
            s.id                AS session_id,
            s.timestamp         AS datetime,
            COALESCE(e.name, 'Sin ejercicio') AS exercise_name,
            s.notes,
            COUNT(m.id)         AS metric_count
        FROM sessions s
        LEFT JOIN exercises e ON s.exercise_id = e.id
        LEFT JOIN metrics m   ON m.session_id  = s.id
        WHERE s.patient_id = ?
        GROUP BY s.id
        ORDER BY s.timestamp DESC
        """,
        (patient_id,),
        label="get_patient_sessions",
    )


def get_session_summary(session_id: int) -> dict[str, Any]:
    """Return a full session bundle: session header, patient, exercise, and aggregated metrics."""
    log.debug("get_session_summary called with session_id=%s", session_id)
    rows = _safe_execute(
        """
        SELECT
            s.id                AS session_id,
            s.timestamp         AS datetime,
            s.notes             AS session_notes,
            p.id                AS patient_id,
            p.name              AS patient_name,
            p.age               AS patient_age,
            p.gender            AS patient_gender,
            COALESCE(e.name, 'Sin ejercicio') AS exercise_name
        FROM sessions s
        LEFT JOIN patients  p ON s.patient_id  = p.id
        LEFT JOIN exercises e ON s.exercise_id = e.id
        WHERE s.id = ?
        """,
        (session_id,),
        label="get_session_summary_header",
    )

    if not rows:
        log.warning("[query_engine] Session %s not found.", session_id)
        return {}

    header = rows[0]

    metrics = get_session_metrics(session_id)

    return {
        "session": {
            "id": header["session_id"],
            "datetime": header["datetime"],
            "notes": header["session_notes"],
        },
        "patient": {
            "id": header["patient_id"],
            "name": header["patient_name"],
            "age": header["patient_age"],
            "gender": header["patient_gender"],
        },
        "exercise": header["exercise_name"],
        "metrics": metrics,
    }


def get_session_metrics(session_id: int) -> list[dict[str, Any]]:
    """Return all metric rows for the given session."""
    log.debug("get_session_metrics called with session_id=%s", session_id)
    return _safe_execute(
        """
        SELECT metric_name, metric_value, unit
        FROM metrics
        WHERE session_id = ?
        ORDER BY metric_name
        """,
        (session_id,),
        label="get_session_metrics",
    )


def get_patient_evolution(
    patient_id: int,
    metric_name: str,
) -> list[dict[str, Any]]:
    """
    Return the temporal evolution of a metric for a patient, one row per session in chronological order.

    metric_name accepts either a fully-suffixed name (e.g. 'angle_arm_r_max')
    or the base series (e.g. 'angle_arm_r'), in which case the _min/_max/_range rows are returned together.
    """
    log.debug(
        "get_patient_evolution called with patient_id=%s, metric_name=%s",
        patient_id, metric_name
    )
    suffixes = ("_min", "_max", "_range")
    if not any(metric_name.endswith(s) for s in suffixes):
        like_pattern = f"{metric_name}%"
        log.debug("[query_engine] Using LIKE pattern for full series: %s", like_pattern)
    else:
        like_pattern = metric_name
        log.debug("[query_engine] Using exact metric_name: %s", like_pattern)

    return _safe_execute(
        """
        SELECT
            s.id                AS session_id,
            s.timestamp         AS datetime,
            COALESCE(e.name, 'Sin ejercicio') AS exercise_name,
            m.metric_name,
            m.metric_value,
            m.unit
        FROM metrics m
        JOIN sessions s   ON s.id = m.session_id
        LEFT JOIN exercises e ON e.id = s.exercise_id
        WHERE s.patient_id  = ?
          AND m.metric_name LIKE ?
        ORDER BY s.timestamp ASC, m.metric_name ASC
        """,
        (patient_id, like_pattern),
        label="get_patient_evolution",
    )


def get_all_metrics_latest_session(patient_id: int) -> list[dict[str, Any]]:
    """Return the metrics of the patient's most recent session (a quick current-state snapshot)."""
    log.debug("get_all_metrics_latest_session called with patient_id=%s", patient_id)
    return _safe_execute(
        """
        SELECT
            s.id            AS session_id,
            s.timestamp     AS datetime,
            m.metric_name,
            m.metric_value,
            m.unit
        FROM metrics m
        JOIN sessions s ON s.id = m.session_id
        WHERE s.patient_id = ?
          AND s.id = (
              SELECT id FROM sessions
              WHERE patient_id = ?
              ORDER BY timestamp DESC
              LIMIT 1
          )
        ORDER BY m.metric_name
        """,
        (patient_id, patient_id),
        label="get_all_metrics_latest_session",
    )


def compare_sessions(
    session_id_a: int,
    session_id_b: int,
) -> dict[str, Any]:
    """Compare two sessions and return per-metric absolute delta and percent change for shared metrics."""
    log.debug(
        "compare_sessions called with session_id_a=%s, session_id_b=%s",
        session_id_a, session_id_b
    )
    metrics_a = {r["metric_name"]: r for r in get_session_metrics(session_id_a)}
    metrics_b = {r["metric_name"]: r for r in get_session_metrics(session_id_b)}

    shared_keys = sorted(set(metrics_a) & set(metrics_b))

    comparison = []
    for key in shared_keys:
        val_a = metrics_a[key]["metric_value"]
        val_b = metrics_b[key]["metric_value"]
        delta = round(val_b - val_a, 4)
        pct = round((delta / val_a * 100), 2) if val_a != 0 else None
        comparison.append(
            {
                "metric_name": key,
                "value_a": val_a,
                "value_b": val_b,
                "delta": delta,
                "pct_change": pct,
                "unit": metrics_a[key]["unit"],
            }
        )

    def _session_header(sid: int) -> dict[str, Any]:
        rows = _safe_execute(
            """
            SELECT s.id, s.timestamp AS datetime,
                   p.name AS patient_name,
                   COALESCE(e.name, 'Sin ejercicio') AS exercise_name
            FROM sessions s
            LEFT JOIN patients  p ON p.id = s.patient_id
            LEFT JOIN exercises e ON e.id = s.exercise_id
            WHERE s.id = ?
            """,
            (sid,),
            label="compare_sessions_header",
        )
        return rows[0] if rows else {}

    return {
        "session_a": _session_header(session_id_a),
        "session_b": _session_header(session_id_b),
        "comparison": comparison,
    }
