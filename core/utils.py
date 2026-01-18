"""
Utilidades compartidas para Recon IA.
Compatible con PyInstaller.

ACTUALIZADO: Migrado a usar path_manager para todas las rutas.
"""

import os
import sys
from datetime import datetime
from pathlib import Path

# Importar path_manager como fuente principal de rutas
from core.path_manager import (
    get_app_data_dir,
    get_app_root,
    get_safe_filename as path_manager_get_safe_filename,
    check_disk_space as path_manager_check_disk_space
)


def get_base_directory():
    """
    DEPRECATED: Usar path_manager.get_app_root() en su lugar.
    
    Obtiene el directorio base de la aplicación.
    
    Returns:
        str: Ruta al directorio base (donde está el .exe o el proyecto)
    """
    import warnings
    warnings.warn(
        "get_base_directory() está deprecado. Usa path_manager.get_app_root() en su lugar.",
        DeprecationWarning,
        stacklevel=2
    )
    return str(get_app_root())


def ensure_dir(path: str) -> str:
    """
    Asegura que un directorio exista, creándolo si es necesario.
    
    ACTUALIZADO: Wrapper sobre Path.mkdir() que usa path_manager internamente.
    
    Args:
        path: Ruta del directorio (relativa o absoluta)
    
    Returns:
        str: Ruta absoluta del directorio creado
    """
    path_obj = Path(path)
    
    # Si es ruta relativa, hacerla relativa al directorio de datos de la app
    if not path_obj.is_absolute():
        path_obj = get_app_data_dir() / path
    
    path_obj.mkdir(parents=True, exist_ok=True)
    return str(path_obj)


def timestamp() -> str:
    """
    Genera timestamp para nombres de archivo.
    
    Returns:
        str: Timestamp en formato YYYYMMDD_HHMMSS
    """
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def safe_round(value, decimals=2):
    """
    Redondea un valor de forma segura manejando None y NaN.
    
    Args:
        value: Valor a redondear
        decimals: Número de decimales
    
    Returns:
        float o None
    """
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
    """
    Obtiene la versión de la aplicación.
    
    Returns:
        str: Versión en formato X.Y.Z
    """
    # TODO: Leer de un archivo VERSION o __init__.py
    return "1.0.0"


# Wrapper functions para compatibilidad con código existente
def get_safe_filename(original_name: str, prefix: str = "") -> str:
    """
    Wrapper sobre path_manager.get_safe_filename() para compatibilidad.
    
    Args:
        original_name: Nombre original del archivo
        prefix: Prefijo opcional
    
    Returns:
        str: Nombre sanitizado
    """
    return path_manager_get_safe_filename(original_name, prefix)


def check_disk_space(required_mb: int = 100):
    """
    Wrapper sobre path_manager.check_disk_space() para compatibilidad.
    
    Args:
        required_mb: Megabytes requeridos
    
    Returns:
        tuple: (hay_espacio: bool, mb_disponibles: int)
    """
    return path_manager_check_disk_space(required_mb)


# Auto-test
if __name__ == "__main__":
    print("=" * 60)
    print("PRUEBA DE UTILIDADES")
    print("=" * 60)
    
    print(f"\nVersion: {get_app_version()}")
    print(f"Timestamp: {timestamp()}")
    
    print("\nSafe round:")
    print(f"  safe_round(3.14159, 2) = {safe_round(3.14159, 2)}")
    print(f"  safe_round(None, 2) = {safe_round(None, 2)}")
    print(f"  safe_round(float('nan'), 2) = {safe_round(float('nan'), 2)}")
    
    print("\nSafe filename:")
    print(f"  get_safe_filename('test video.mp4') = {get_safe_filename('test video.mp4')}")
    
    print("\nDisk space:")
    has_space, available = check_disk_space(100)
    print(f"  check_disk_space(100) = {has_space}, {available}MB")
    
    print("\nEnsure dir (test):")
    test_dir = ensure_dir("test_temp_dir")
    print(f"  Created: {test_dir}")
    print(f"  Exists: {Path(test_dir).exists()}")
    
    # Limpiar directorio de prueba
    import shutil
    if Path(test_dir).exists():
        shutil.rmtree(test_dir)
        print(f"  Cleaned up test directory")
    
    print("\n" + "=" * 60)