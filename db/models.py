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

CREATE_TABLE_EXERCISES = """
CREATE TABLE IF NOT EXISTS exercises (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    description TEXT
);
"""

CREATE_TABLE_SESSIONS = """
CREATE TABLE IF NOT EXISTS sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    patient_id INTEGER NOT NULL,
    exercise_id INTEGER,
    
    video_path_raw TEXT,
    video_path_mediapipe TEXT,
    video_path_legacy TEXT,
    video_path TEXT,
    
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    notes TEXT,
    FOREIGN KEY (patient_id) REFERENCES patients(id) ON DELETE CASCADE,
    FOREIGN KEY (exercise_id) REFERENCES exercises(id) ON DELETE SET NULL
);
"""

CREATE_TABLE_MOVEMENT_DATA = """
CREATE TABLE IF NOT EXISTS movement_data (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id INTEGER NOT NULL,
    time_seconds REAL,
    frame INTEGER,

    shoulder_x_r REAL, shoulder_y_r REAL,
    elbow_x_r REAL, elbow_y_r REAL,
    wrist_x_r REAL, wrist_y_r REAL,
    angle_arm_r REAL,

    shoulder_x_l REAL, shoulder_y_l REAL,
    elbow_x_l REAL, elbow_y_l REAL,
    wrist_x_l REAL, wrist_y_l REAL,
    angle_arm_l REAL,

    hip_x_r REAL, hip_y_r REAL,
    knee_x_r REAL, knee_y_r REAL,
    ankle_x_r REAL, ankle_y_r REAL,
    angle_leg_r REAL,

    heel_x_r REAL, heel_y_r REAL,
    foot_index_x_r REAL, foot_index_y_r REAL,

    hip_x_l REAL, hip_y_l REAL,
    knee_x_l REAL, knee_y_l REAL,
    ankle_x_l REAL, ankle_y_l REAL,
    angle_leg_l REAL,

    heel_x_l REAL, heel_y_l REAL,
    foot_index_x_l REAL, foot_index_y_l REAL,

    symmetry_angle_arm REAL,
    symmetry_angle_leg REAL,
    
    symmetry_shoulder_y REAL,
    symmetry_elbow_y REAL,
    symmetry_knee_y REAL,

    FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE
);
"""

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

CREATE_TABLE_FEEDBACK = """
CREATE TABLE IF NOT EXISTS feedback (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    component TEXT NOT NULL,
    feedback_type TEXT NOT NULL,
    title TEXT NOT NULL,
    description TEXT NOT NULL,
    user_agent TEXT,
    screen_resolution TEXT,
    status TEXT DEFAULT 'pending' CHECK(status IN ('pending', 'reviewed', 'resolved')),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""

TABLES = [
    CREATE_TABLE_PATIENTS,
    CREATE_TABLE_EXERCISES,
    CREATE_TABLE_SESSIONS,
    CREATE_TABLE_MOVEMENT_DATA,
    CREATE_TABLE_METRICS,
    CREATE_TABLE_FEEDBACK,
]