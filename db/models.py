"""
Database schema definition for the Recon IA system.
This module defines the SQL table creation statements required to initialize
the local SQLite database used for patient management, session tracking, 
and biomechanical data storage.

NUEVO: 
- Incluye columnas de simetría bilateral para análisis comparativo
- Soporte para 3 versiones de vídeo por sesión (raw, mediapipe, legacy)
"""

# ============================================================
# PATIENTS
# ============================================================

CREATE_TABLE_PATIENTS = """
CREATE TABLE IF NOT EXISTS patients (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    dni TEXT UNIQUE,
    age INTEGER,
    gender TEXT CHECK(gender IN ('M', 'F', 'Other')),
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""

# ============================================================
# EXERCISES
# ============================================================

CREATE_TABLE_EXERCISES = """
CREATE TABLE IF NOT EXISTS exercises (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    description TEXT
);
"""

# ============================================================
# SESSIONS
# ============================================================

CREATE_TABLE_SESSIONS = """
CREATE TABLE IF NOT EXISTS sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    patient_id INTEGER NOT NULL,
    exercise_id INTEGER,
    
    -- ============================================================
    -- VIDEO PATHS - Múltiples versiones de salida
    -- ============================================================
    video_path_raw TEXT,        -- Vídeo sin procesar (original, sin overlays)
    video_path_mediapipe TEXT,  -- Vídeo con overlay MediaPipe completo (33 landmarks)
    video_path_legacy TEXT,     -- Vídeo con overlay clínico personalizado (barritas y puntos)
    
    -- Columna legacy (deprecated, mantener por compatibilidad)
    video_path TEXT,            -- Apunta al vídeo principal (normalmente legacy)
    
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    notes TEXT,
    FOREIGN KEY (patient_id) REFERENCES patients(id) ON DELETE CASCADE,
    FOREIGN KEY (exercise_id) REFERENCES exercises(id) ON DELETE SET NULL
);
"""

# ============================================================
# MOVEMENT DATA
# ============================================================

CREATE_TABLE_MOVEMENT_DATA = """
CREATE TABLE IF NOT EXISTS movement_data (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id INTEGER NOT NULL,
    time_seconds REAL,
    frame INTEGER,

    -- Right arm
    shoulder_x_r REAL, shoulder_y_r REAL,
    elbow_x_r REAL, elbow_y_r REAL,
    wrist_x_r REAL, wrist_y_r REAL,
    angle_arm_r REAL,

    -- Left arm
    shoulder_x_l REAL, shoulder_y_l REAL,
    elbow_x_l REAL, elbow_y_l REAL,
    wrist_x_l REAL, wrist_y_l REAL,
    angle_arm_l REAL,

    -- Right leg
    hip_x_r REAL, hip_y_r REAL,
    knee_x_r REAL, knee_y_r REAL,
    ankle_x_r REAL, ankle_y_r REAL,
    angle_leg_r REAL,

    -- Right foot
    heel_x_r REAL, heel_y_r REAL,
    foot_index_x_r REAL, foot_index_y_r REAL,

    -- Left leg
    hip_x_l REAL, hip_y_l REAL,
    knee_x_l REAL, knee_y_l REAL,
    ankle_x_l REAL, ankle_y_l REAL,
    angle_leg_l REAL,

    -- Left foot
    heel_x_l REAL, heel_y_l REAL,
    foot_index_x_l REAL, foot_index_y_l REAL,

    -- ============================================================
    -- BILATERAL SYMMETRY METRICS
    -- ============================================================
    -- Valores cercanos a 0 indican simetría perfecta
    -- Valores altos indican asimetría/compensación
    
    -- Angular symmetry (degrees)
    symmetry_angle_arm REAL,  -- Diferencia angular entre brazos
    symmetry_angle_leg REAL,  -- Diferencia angular entre piernas
    
    -- Positional symmetry (pixels)
    symmetry_shoulder_y REAL, -- Diferencia vertical entre hombros
    symmetry_elbow_y REAL,    -- Diferencia vertical entre codos
    symmetry_knee_y REAL,     -- Diferencia vertical entre rodillas

    FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE
);
"""

# ============================================================
# METRICS
# ============================================================

CREATE_TABLE_METRICS = """
CREATE TABLE IF NOT EXISTS metrics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id INTEGER NOT NULL,
    metric_name TEXT NOT NULL,
    metric_value REAL NOT NULL,
    unit TEXT,
    FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE
);
"""

# ============================================================
# TABLE REGISTRY
# ============================================================

TABLES = [
    CREATE_TABLE_PATIENTS,
    CREATE_TABLE_EXERCISES,
    CREATE_TABLE_SESSIONS,
    CREATE_TABLE_MOVEMENT_DATA,
    CREATE_TABLE_METRICS,
]