# db/crud.py
"""
CRUD operations para la base de datos SQLite.
Gestiona pacientes, ejercicios, sesiones, datos de movimiento y métricas.

NUEVO: 
- Soporte optimizado para columnas dinámicas en movement_data
- Métricas de simetría bilateral
- Múltiples versiones de vídeo por sesión
"""

import sqlite3
from typing import List, Dict, Any, Tuple
from db.init_db import get_connection


# ============================================================
# PACIENTES
# ============================================================

def create_patient(
    name: str,
    dni: str | None = None,
    age: int | None = None,
    gender: str | None = None,
    notes: str | None = None
) -> int:
    """
    Crea un nuevo paciente.
    
    Args:
        name: Nombre del paciente (requerido)
        dni: DNI/identificación (único, opcional)
        age: Edad (opcional)
        gender: Género (M, F, Other)
        notes: Notas adicionales
    
    Returns:
        ID del paciente creado
    
    Raises:
        ValueError: Si gender no es válido o DNI duplicado
    """
    # Validaciones
    if gender and gender not in ("M", "F", "Other"):
        raise ValueError(f"Género inválido: {gender}. Use 'M', 'F' o 'Other'")
    
    with get_connection() as conn:
        cur = conn.cursor()
        
        # Verificar DNI único
        if dni:
            cur.execute("SELECT id FROM patients WHERE dni = ?", (dni,))
            if cur.fetchone():
                raise ValueError(f"Ya existe un paciente con DNI: {dni}")
        
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
    """
    Obtiene todos los pacientes.
    
    Returns:
        Lista de tuplas: (id, name, dni, age, gender, notes, created_at)
    """
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            "SELECT id, name, dni, age, gender, notes, created_at FROM patients ORDER BY name"
        )
        return cur.fetchall()


def get_patient_by_id(patient_id: int) -> Tuple | None:
    """Obtiene un paciente por ID."""
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
    """
    Actualiza un paciente existente.
    
    Returns:
        True si se actualizó, False si no existe
    """
    if gender and gender not in ("M", "F", "Other"):
        raise ValueError(f"Género inválido: {gender}")
    
    with get_connection() as conn:
        cur = conn.cursor()
        
        # Construir UPDATE dinámico
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
    """
    Elimina un paciente.
    
    Args:
        patient_id: ID del paciente
        cascade: Si True, elimina también sus sesiones y datos asociados
    
    Returns:
        True si se eliminó
    """
    with get_connection() as conn:
        cur = conn.cursor()
        
        if cascade:
            # Obtener sesiones del paciente
            cur.execute("SELECT id FROM sessions WHERE patient_id = ?", (patient_id,))
            session_ids = [row[0] for row in cur.fetchall()]
            
            # Eliminar datos asociados a cada sesión
            for sid in session_ids:
                cur.execute("DELETE FROM movement_data WHERE session_id = ?", (sid,))
                cur.execute("DELETE FROM metrics WHERE session_id = ?", (sid,))
            
            # Eliminar sesiones
            cur.execute("DELETE FROM sessions WHERE patient_id = ?", (patient_id,))
        
        # Eliminar paciente
        cur.execute("DELETE FROM patients WHERE id = ?", (patient_id,))
        conn.commit()
        return cur.rowcount > 0


# ============================================================
# EJERCICIOS
# ============================================================

def create_exercise(name: str, description: str | None = None) -> int:
    """Crea un nuevo ejercicio (o retorna existente)."""
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            "INSERT OR IGNORE INTO exercises (name, description) VALUES (?, ?)",
            (name, description)
        )
        if cur.lastrowid:
            conn.commit()
            return cur.lastrowid
        
        # Si ya existía, obtener su ID
        cur.execute("SELECT id FROM exercises WHERE name = ?", (name,))
        row = cur.fetchone()
        return row[0] if row else 0


def get_all_exercises() -> List[Tuple]:
    """
    Obtiene todos los ejercicios.
    
    Returns:
        Lista de tuplas: (id, name, description)
    """
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("SELECT id, name, description FROM exercises ORDER BY name")
        return cur.fetchall()


def update_exercise(exercise_id: int, name: str | None = None, description: str | None = None) -> bool:
    """Actualiza un ejercicio."""
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
    """Elimina un ejercicio (y opcionalmente sus sesiones)."""
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


# ============================================================
# SESIONES
# ============================================================

def create_session(
    patient_id: int | None = None,
    exercise_id: int | None = None,
    video_path_raw: str | None = None,
    video_path_mediapipe: str | None = None,
    video_path_legacy: str | None = None,
    notes: str | None = None
) -> int:
    """
    Crea una nueva sesión de análisis.
    
    Args:
        patient_id: ID del paciente
        exercise_id: ID del ejercicio
        video_path_raw: Ruta al vídeo sin procesar (opcional)
        video_path_mediapipe: Ruta al vídeo con overlay MediaPipe (opcional)
        video_path_legacy: Ruta al vídeo con overlay clínico (opcional)
        notes: Notas clínicas
    
    Returns:
        ID de la sesión creada
    """
    with get_connection() as conn:
        cur = conn.cursor()
        
        # video_path legacy: apunta al vídeo principal (preferencia: legacy > mediapipe > raw)
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
    """
    Obtiene todas las sesiones con datos relacionados.
    
    Returns:
        Lista de diccionarios con datos de sesión + paciente + ejercicio + rutas de vídeo
    """
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
    """
    Obtiene sesiones de un paciente específico.
    
    Returns:
        Lista de diccionarios con datos de sesión + ejercicio + rutas de vídeo
    """
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
    """Elimina una sesión y todos sus datos asociados (cascade)."""
    with get_connection() as conn:
        cur = conn.cursor()
        
        # Eliminar datos de movimiento
        cur.execute("DELETE FROM movement_data WHERE session_id = ?", (session_id,))
        
        # Eliminar métricas
        cur.execute("DELETE FROM metrics WHERE session_id = ?", (session_id,))
        
        # Eliminar sesión
        cur.execute("DELETE FROM sessions WHERE id = ?", (session_id,))
        
        conn.commit()
        return cur.rowcount > 0


# ============================================================
# MOVEMENT DATA (con columnas dinámicas)
# ============================================================

def add_movement_data(session_id: int, data: Dict[str, Any]) -> None:
    """
    Inserta datos de movimiento por frame con columnas dinámicas.
    
    OPTIMIZADO: Construye INSERT dinámico basado en las keys del dict.
    Soporta cualquier número de columnas (posiciones, ángulos, simetrías, etc.)
    
    Args:
        session_id: ID de la sesión
        data: Diccionario con datos del frame
              Ej: {"time_seconds": 1.5, "frame": 45, "angle_arm_r": 120.5, 
                   "symmetry_shoulder_y": 5.2, ...}
    
    Raises:
        sqlite3.Error: Si falla la inserción
    """
    if not data:
        return
    
    # Añadir session_id al diccionario
    data["session_id"] = session_id
    
    # Construir INSERT dinámico
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
    """
    Obtiene todos los datos de movimiento de una sesión.
    
    Returns:
        Lista de diccionarios con todos los campos almacenados
    """
    with get_connection() as conn:
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute(
            "SELECT * FROM movement_data WHERE session_id = ? ORDER BY frame",
            (session_id,)
        )
        return [dict(row) for row in cur.fetchall()]


# ============================================================
# MÉTRICAS
# ============================================================

def add_metric(
    session_id: int,
    metric_name: str,
    metric_value: float,
    unit: str | None = None
) -> None:
    """
    Añade una métrica agregada a una sesión.
    
    Args:
        session_id: ID de la sesión
        metric_name: Nombre de la métrica (ej: "angle_arm_r_max", "symmetry_shoulder_y_min")
        metric_value: Valor numérico
        unit: Unidad de medida ("degrees", "pixels", etc.)
    """
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
    """
    Obtiene todas las métricas de una sesión.
    
    Returns:
        Lista de tuplas: (metric_name, metric_value, unit)
    """
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            "SELECT metric_name, metric_value, unit FROM metrics WHERE session_id = ? ORDER BY metric_name",
            (session_id,)
        )
        return cur.fetchall()


# ============================================================
# UTILIDADES
# ============================================================

def get_table_counts() -> Dict[str, int]:
    """
    Obtiene conteos de registros en tablas principales.
    
    Returns:
        Diccionario con conteos: {"patients": X, "exercises": Y, ...}
    """
    with get_connection() as conn:
        cur = conn.cursor()
        
        counts = {}
        for table in ["patients", "exercises", "sessions", "metrics"]:
            cur.execute(f"SELECT COUNT(*) FROM {table}")
            counts[table] = cur.fetchone()[0]
        
        return counts