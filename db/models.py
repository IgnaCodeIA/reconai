"""
Define el esquema de la base de datos local de Recon IA.
Contiene las sentencias SQL para crear las tablas necesarias:
patients, exercises, sessions y metrics.
"""

# Esquema de creación de tablas (usado en init_db.py)

CREATE_TABLE_PATIENTS = """
CREATE TABLE IF NOT EXISTS patients (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    age INTEGER,
    gender TEXT CHECK(gender IN ('M', 'F', 'Otro')),
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
    csv_path TEXT,
    video_path TEXT,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (patient_id) REFERENCES patients(id) ON DELETE CASCADE,
    FOREIGN KEY (exercise_id) REFERENCES exercises(id) ON DELETE SET NULL
);
"""

CREATE_TABLE_METRICS = """
CREATE TABLE IF NOT EXISTS metrics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id INTEGER NOT NULL,
    metric_name TEXT NOT NULL,
    metric_value REAL NOT NULL,
    FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE
);
"""

TABLES = [
    CREATE_TABLE_PATIENTS,
    CREATE_TABLE_EXERCISES,
    CREATE_TABLE_SESSIONS,
    CREATE_TABLE_METRICS,
]
