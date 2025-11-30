# db/feedback_crud.py
"""
CRUD operations para feedback de usuarios.
Permite a usuarios clínicos reportar problemas, sugerencias y comentarios.
"""

import sqlite3
from typing import List, Dict, Any, Tuple
from db.init_db import get_connection


# ============================================================
# CREAR FEEDBACK
# ============================================================

def create_feedback(
    component: str,
    feedback_type: str,
    title: str,
    description: str,
    user_agent: str | None = None,
    screen_resolution: str | None = None
) -> int:
    """
    Crea un nuevo registro de feedback.
    
    Args:
        component: Componente afectado (ej: "Sesiones - Captura de video")
        feedback_type: Tipo de feedback (ej: "Problema o error")
        title: Título breve (max 100 caracteres)
        description: Descripción detallada (max 500 caracteres)
        user_agent: Navegador/OS (capturado automáticamente)
        screen_resolution: Resolución de pantalla (capturado automáticamente)
    
    Returns:
        ID del feedback creado
    
    Raises:
        ValueError: Si faltan campos obligatorios o exceden límites
    """
    # Validaciones
    if not component or not feedback_type or not title or not description:
        raise ValueError("Todos los campos obligatorios deben estar completos")
    
    if len(title) > 100:
        raise ValueError("El título no puede exceder 100 caracteres")
    
    if len(description) > 500:
        raise ValueError("La descripción no puede exceder 500 caracteres")
    
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO feedback (
                component, feedback_type, title, description,
                user_agent, screen_resolution
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (component, feedback_type, title, description, user_agent, screen_resolution)
        )
        conn.commit()
        return cur.lastrowid


# ============================================================
# CONSULTAR FEEDBACK
# ============================================================

def get_all_feedback(status_filter: str | None = None) -> List[Dict[str, Any]]:
    """
    Obtiene todos los registros de feedback.
    
    Args:
        status_filter: Filtrar por estado ('pending', 'resolved', 'archived')
                       Si es None, devuelve todos
    
    Returns:
        Lista de diccionarios con datos de feedback
    """
    with get_connection() as conn:
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        
        if status_filter:
            cur.execute(
                """
                SELECT * FROM feedback 
                WHERE status = ? 
                ORDER BY submitted_at DESC
                """,
                (status_filter,)
            )
        else:
            cur.execute("SELECT * FROM feedback ORDER BY submitted_at DESC")
        
        return [dict(row) for row in cur.fetchall()]


def get_feedback_by_id(feedback_id: int) -> Dict[str, Any] | None:
    """Obtiene un feedback específico por ID."""
    with get_connection() as conn:
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute("SELECT * FROM feedback WHERE id = ?", (feedback_id,))
        row = cur.fetchone()
        return dict(row) if row else None


# ============================================================
# ACTUALIZAR FEEDBACK
# ============================================================

def update_feedback_status(feedback_id: int, new_status: str) -> bool:
    """
    Actualiza el estado de un feedback.
    
    Args:
        feedback_id: ID del feedback
        new_status: Nuevo estado ('pending', 'resolved', 'archived')
    
    Returns:
        True si se actualizó correctamente
    """
    if new_status not in ('pending', 'resolved', 'archived'):
        raise ValueError(f"Estado inválido: {new_status}")
    
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            "UPDATE feedback SET status = ? WHERE id = ?",
            (new_status, feedback_id)
        )
        conn.commit()
        return cur.rowcount > 0


# ============================================================
# ELIMINAR FEEDBACK
# ============================================================

def delete_feedback(feedback_id: int) -> bool:
    """Elimina un registro de feedback."""
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("DELETE FROM feedback WHERE id = ?", (feedback_id,))
        conn.commit()
        return cur.rowcount > 0


# ============================================================
# ESTADÍSTICAS
# ============================================================

def get_feedback_stats() -> Dict[str, Any]:
    """
    Obtiene estadísticas agregadas de feedback.
    
    Returns:
        Diccionario con:
        - total: Total de feedbacks
        - by_component: Conteo por componente
        - by_type: Conteo por tipo
        - by_status: Conteo por estado
        - recent_count: Feedbacks de últimos 7 días
    """
    with get_connection() as conn:
        cur = conn.cursor()
        
        # Total
        cur.execute("SELECT COUNT(*) FROM feedback")
        total = cur.fetchone()[0]
        
        # Por componente
        cur.execute("""
            SELECT component, COUNT(*) as count 
            FROM feedback 
            GROUP BY component 
            ORDER BY count DESC
        """)
        by_component = dict(cur.fetchall())
        
        # Por tipo
        cur.execute("""
            SELECT feedback_type, COUNT(*) as count 
            FROM feedback 
            GROUP BY feedback_type 
            ORDER BY count DESC
        """)
        by_type = dict(cur.fetchall())
        
        # Por estado
        cur.execute("""
            SELECT status, COUNT(*) as count 
            FROM feedback 
            GROUP BY status
        """)
        by_status = dict(cur.fetchall())
        
        # Últimos 7 días
        cur.execute("""
            SELECT COUNT(*) 
            FROM feedback 
            WHERE submitted_at >= datetime('now', '-7 days')
        """)
        recent_count = cur.fetchone()[0]
        
        return {
            "total": total,
            "by_component": by_component,
            "by_type": by_type,
            "by_status": by_status,
            "recent_count": recent_count
        }