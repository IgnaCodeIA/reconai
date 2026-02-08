"""
Gestión centralizada de rutas para Recon IA.
Compatible con PyInstaller - persiste datos fuera del ejecutable.
"""

import os
import sys
import shutil
from pathlib import Path
from typing import Tuple
import re


def get_app_data_dir() -> Path:
    if sys.platform == 'win32':
        appdata = os.environ.get('LOCALAPPDATA', os.path.expanduser('~/AppData/Local'))
        data_dir = Path(appdata) / 'ReconIA'
    elif sys.platform == 'darwin':
        data_dir = Path.home() / 'Library' / 'Application Support' / 'ReconIA'
    else:
        data_dir = Path.home() / '.local' / 'share' / 'ReconIA'
    
    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir


def get_app_root() -> Path:
    if getattr(sys, 'frozen', False):
        return Path(sys.executable).parent
    else:
        return Path(__file__).parent.parent


def get_uploads_dir() -> Path:
    uploads = get_app_data_dir() / 'uploads'
    uploads.mkdir(exist_ok=True)
    (uploads / 'videos').mkdir(exist_ok=True)
    (uploads / 'images').mkdir(exist_ok=True)
    return uploads


def get_temp_dir() -> Path:
    temp = get_app_data_dir() / 'temp'
    temp.mkdir(exist_ok=True)
    return temp


def get_exports_dir() -> Path:
    exports = get_app_data_dir() / "exports"
    exports.mkdir(parents=True, exist_ok=True)
    return exports


def get_database_dir() -> Path:
    db_dir = get_app_data_dir() / 'database'
    db_dir.mkdir(exist_ok=True)
    return db_dir


def get_logs_dir() -> Path:
    logs = get_app_data_dir() / 'logs'
    logs.mkdir(exist_ok=True)
    return logs


def get_db_path() -> Path:
    return get_database_dir() / 'sessions.db'


def get_log_path() -> Path:
    return get_logs_dir() / 'recon_ia.log'


def get_safe_filename(original_name: str, prefix: str = "") -> str:
    name = Path(original_name).name
    
    dangerous_chars = ['..', '/', '\\', '<', '>', ':', '"', '|', '?', '*']
    for char in dangerous_chars:
        name = name.replace(char, '_')
    
    name = name.replace(' ', '_')
    name = re.sub(r'[^\x00-\x7F]+', '_', name)
    
    if prefix:
        name = f"{prefix}{name}"
    
    max_length = 200
    if len(name) > max_length:
        ext = Path(name).suffix
        name_without_ext = Path(name).stem
        max_stem_length = max_length - len(ext)
        name = name_without_ext[:max_stem_length] + ext
    
    return name


def check_disk_space(required_mb: int = 100) -> Tuple[bool, int]:
    try:
        stat = shutil.disk_usage(get_app_data_dir())
        available_mb = stat.free / (1024 * 1024)
        has_space = available_mb >= required_mb
        return (has_space, int(available_mb))
    except Exception as e:
        print(f"Error al verificar espacio en disco: {e}")
        return (True, 0)


def get_disk_usage_stats() -> dict:
    try:
        stat = shutil.disk_usage(get_app_data_dir())
        
        app_data_size = 0
        for dirpath, dirnames, filenames in os.walk(get_app_data_dir()):
            for filename in filenames:
                filepath = Path(dirpath) / filename
                try:
                    app_data_size += filepath.stat().st_size
                except:
                    pass
        
        return {
            'total_gb': round(stat.total / (1024**3), 2),
            'used_gb': round(stat.used / (1024**3), 2),
            'free_gb': round(stat.free / (1024**3), 2),
            'percent_used': round((stat.used / stat.total) * 100, 1),
            'app_data_size_mb': round(app_data_size / (1024**2), 2)
        }
    except Exception as e:
        print(f"Error calculando uso de disco: {e}")
        return {
            'total_gb': 0,
            'used_gb': 0,
            'free_gb': 0,
            'percent_used': 0,
            'app_data_size_mb': 0
        }


def initialize_directories():
    get_uploads_dir()
    get_temp_dir()
    get_exports_dir()
    get_database_dir()
    get_logs_dir()


try:
    initialize_directories()
except Exception as e:
    print(f"Error inicializando directorios: {e}")