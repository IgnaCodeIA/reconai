import sqlite3
from typing import List, Dict, Any
from db.init_db import get_connection
from core.logger import get_logger

log = get_logger("db.feedback_crud")


def create_feedback(
    component: str,
    feedback_type: str,
    title: str,
    description: str,
    user_agent: str | None = None,
    screen_resolution: str | None = None
) -> int:
    """Insert a feedback row in 'pending' status and return its id."""
    log.debug(
        "create_feedback called with component=%s, feedback_type=%s, title=%s",
        component, feedback_type, title
    )
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO feedback (
                component, feedback_type, title, description,
                user_agent, screen_resolution, status
            )
            VALUES (?, ?, ?, ?, ?, ?, 'pending')
            """,
            (component, feedback_type, title, description, user_agent, screen_resolution)
        )
        conn.commit()
        return cur.lastrowid


def get_all_feedback(status: str | None = None) -> List[Dict[str, Any]]:
    """Return all feedback rows, optionally filtered by status, newest first."""
    log.debug("get_all_feedback called with status=%s", status)
    with get_connection() as conn:
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()

        if status:
            cur.execute(
                """
                SELECT id, component, feedback_type, title, description,
                       user_agent, screen_resolution, status, created_at
                FROM feedback
                WHERE status = ?
                ORDER BY created_at DESC
                """,
                (status,)
            )
        else:
            cur.execute(
                """
                SELECT id, component, feedback_type, title, description,
                       user_agent, screen_resolution, status, created_at
                FROM feedback
                ORDER BY created_at DESC
                """
            )

        return [dict(row) for row in cur.fetchall()]


def get_feedback_by_id(feedback_id: int) -> Dict[str, Any] | None:
    """Return a single feedback row by id, or None if not found."""
    log.debug("get_feedback_by_id called with feedback_id=%s", feedback_id)
    with get_connection() as conn:
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute(
            """
            SELECT id, component, feedback_type, title, description,
                   user_agent, screen_resolution, status, created_at
            FROM feedback
            WHERE id = ?
            """,
            (feedback_id,)
        )
        row = cur.fetchone()
        return dict(row) if row else None


def update_feedback_status(feedback_id: int, status: str) -> bool:
    """Update a feedback row's status. Status must be 'pending', 'reviewed', or 'resolved'."""
    log.debug("update_feedback_status called with feedback_id=%s, status=%s", feedback_id, status)
    if status not in ('pending', 'reviewed', 'resolved'):
        raise ValueError(f"Invalid status: {status}")

    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            "UPDATE feedback SET status = ? WHERE id = ?",
            (status, feedback_id)
        )
        conn.commit()
        return cur.rowcount > 0


def delete_feedback(feedback_id: int) -> bool:
    """Delete a feedback row. Returns True if a row was removed."""
    log.debug("delete_feedback called with feedback_id=%s", feedback_id)
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("DELETE FROM feedback WHERE id = ?", (feedback_id,))
        conn.commit()
        return cur.rowcount > 0


def get_feedback_stats() -> Dict[str, int]:
    """Return counts of feedback rows by status: total, pending, reviewed, resolved."""
    with get_connection() as conn:
        cur = conn.cursor()

        stats = {}

        cur.execute("SELECT COUNT(*) FROM feedback")
        stats['total'] = cur.fetchone()[0]

        cur.execute("SELECT COUNT(*) FROM feedback WHERE status = 'pending'")
        stats['pending'] = cur.fetchone()[0]

        cur.execute("SELECT COUNT(*) FROM feedback WHERE status = 'reviewed'")
        stats['reviewed'] = cur.fetchone()[0]

        cur.execute("SELECT COUNT(*) FROM feedback WHERE status = 'resolved'")
        stats['resolved'] = cur.fetchone()[0]

        return stats
