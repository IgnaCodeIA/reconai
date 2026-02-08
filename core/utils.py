import os
import sys
from datetime import datetime
from pathlib import Path

from core.path_manager import (
    get_app_data_dir,
    get_app_root,
    get_safe_filename as path_manager_get_safe_filename,
    check_disk_space as path_manager_check_disk_space
)


def get_base_directory():
    import warnings
    warnings.warn(
        "get_base_directory() está deprecado. Usa path_manager.get_app_root() en su lugar.",
        DeprecationWarning,
        stacklevel=2
    )
    return str(get_app_root())


def ensure_dir(path: str) -> str:
    path_obj = Path(path)
    
    if not path_obj.is_absolute():
        path_obj = get_app_data_dir() / path
    
    path_obj.mkdir(parents=True, exist_ok=True)
    return str(path_obj)


def timestamp() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def safe_round(value, decimals=2):
    if value is None:
        return None
    try:
        import math
        if math.isnan(value) or math.isinf(value):
            return None
        return round(float(value), decimals)
    except (TypeError, ValueError):
        return None


def get_app_version() -> str:
    return "1.0.0"


def get_safe_filename(original_name: str, prefix: str = "") -> str:
    return path_manager_get_safe_filename(original_name, prefix)


def check_disk_space(required_mb: int = 100):
    return path_manager_check_disk_space(required_mb)