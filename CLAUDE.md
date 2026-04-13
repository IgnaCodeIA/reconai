# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Run the application
streamlit run ui/app.py

# Build Windows executable (requires PyInstaller and FFmpeg on PATH)
python build_exe.py
```

The app runs on port **7860** (configured in `.streamlit/config.toml`).

There are no tests or linting tools configured in this project.

## Architecture

RECON IA is a clinical rehabilitation AI system that performs biomechanical analysis of patient movement via webcam. Built as a Streamlit app with SQLite persistence.

### Layer overview

```
ui/app.py              → Streamlit entry point; routes 6 sidebar sections
ui/components/         → One module per section (sessions, patients, exercises, reports, charts, feedback)
core/                  → Video capture, pose detection, angle math, session orchestration
db/                    → SQLite schema, init, CRUD
reports/pdf_report.py  → ReportLab PDF generation
```

### Core processing pipeline (sessions)

The heaviest module is `ui/components/sessions.py`. When a user records a session:

1. `streamlit-webrtc` streams webcam frames in real time
2. Each frame goes through `core/pose_detection.py` (`PoseDetector`) — a MediaPipe Pose wrapper that extracts 33 landmarks and renders overlays
3. `core/angle_calculator.py` computes joint angles (shoulders, elbows, hips, knees) from 3-point vectors
4. `core/session_manager.py` (`SessionManager`) writes simultaneously to three video outputs:
   - **Raw**: unprocessed frames
   - **MediaPipe**: skeleton overlay
   - **Legacy**: custom clinical overlay from `core/legacy_overlay.py` (color-coded limbs + angle labels)
5. Movement data is sampled and written per-frame to SQLite `movement_data` table (40+ columns)
6. On stop: FFmpeg H.264 encoding is finalized, session record created, metrics aggregated

### Database

SQLite file at `{app_data_dir}/database/sessions.db`, initialized by `db/init_db.py` with WAL mode and foreign keys enabled. Key tables:

- `patients` — demographics
- `exercises` — movement type catalog
- `sessions` — links patient + exercise + video paths
- `movement_data` — per-frame landmarks and angles (right/left pairs for shoulder/elbow/wrist/hip/knee/ankle)
- `metrics` — aggregated min/max/range per session
- `feedback` — in-app bug reports

CRUD is split: `db/crud.py` for clinical data, `db/feedback_crud.py` for feedback.

### Path management

`core/path_manager.py` resolves the app data directory cross-platform and is PyInstaller-aware (detects frozen executables). Data lives at:
- Windows: `%LOCALAPPDATA%\ReconIA\`
- macOS: `~/Library/Application Support/ReconIA/`
- Linux: `~/.local/share/ReconIA/`

Subdirectories: `database/`, `exports/videos/`, `uploads/`, `temp/`, `logs/`.

### Key conventions

- `db/init_db.py` is called at app startup (`ui/app.py`) before any DB access — always ensure `init_db()` is called before CRUD operations
- SQLite connections use `check_same_thread=False` due to Streamlit's threading model
- Logging goes to both console (INFO) and `data/logs/reconia.log` (DEBUG) via `core/logger.py`
- Video frame sampling rate for DB writes is 20 fps target (configurable in `SessionManager`)
