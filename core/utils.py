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
from core.logger import get_logger

log = get_logger("core.utils")


def get_base_directory():
    """Deprecated alias for path_manager.get_app_root()."""
    import warnings
    warnings.warn(
        "get_base_directory() is deprecated. Use path_manager.get_app_root() instead.",
        DeprecationWarning,
        stacklevel=2
    )
    return str(get_app_root())


def ensure_dir(path: str) -> str:
    """Ensure the given directory exists (creating parents) and return its absolute path string."""
    log.debug("ensure_dir called with path=%s", path)
    path_obj = Path(path)

    if not path_obj.is_absolute():
        path_obj = get_app_data_dir() / path

    path_obj.mkdir(parents=True, exist_ok=True)
    return str(path_obj)


def timestamp() -> str:
    """Return the current local time formatted as YYYYMMDD_HHMMSS."""
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def safe_round(value, decimals=2):
    """Round value to N decimals; return None for None, NaN, Inf, or non-numeric input."""
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
    """Return the application version string."""
    return "1.0.0"


def get_safe_filename(original_name: str, prefix: str = "") -> str:
    """Sanitize a filename via path_manager.get_safe_filename."""
    return path_manager_get_safe_filename(original_name, prefix)


def check_disk_space(required_mb: int = 100):
    """Check available disk space via path_manager.check_disk_space."""
    return path_manager_check_disk_space(required_mb)
