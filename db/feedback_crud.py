import sqlite3
from typing import List, Dict, Any, Tuple
from db.init_db import get_connection


def create_feedback(
    component: str,
    feedback_type: str,
    title: str,
    description: str,
    user_agent: str | None = None,
    screen_resolution: str | None = None
) -> int:
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
    if status not in ('pending', 'reviewed', 'resolved'):
        raise ValueError(f"Estado inválido: {status}")
    
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            "UPDATE feedback SET status = ? WHERE id = ?",
            (status, feedback_id)
        )
        conn.commit()
        return cur.rowcount > 0


def delete_feedback(feedback_id: int) -> bool:
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("DELETE FROM feedback WHERE id = ?", (feedback_id,))
        conn.commit()
        return cur.rowcount > 0


def get_feedback_stats() -> Dict[str, int]:
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