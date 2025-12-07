"""
Utilidades compartidas para Recon IA.
Compatible con PyInstaller.
"""

import os
import sys
from datetime import datetime


def get_base_directory():
    """
    Obtiene el directorio base de la aplicación.
    
    Returns:
        str: Ruta al directorio base (donde está el .exe o el proyecto)
    """
    if getattr(sys, 'frozen', False):
        # Ejecutable: directorio del .exe
        return os.path.dirname(sys.executable)
    else:
        # Desarrollo: raíz del proyecto
        return os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


def ensure_dir(path: str) -> str:
    """
    Asegura que un directorio exista, creándolo si es necesario.
    
    CRÍTICO: En ejecutable, crea carpetas relativas al .exe, NO en _MEIPASS.
    
    Args:
        path: Ruta del directorio (relativa o absoluta)
    
    Returns:
        str: Ruta absoluta del directorio creado
    """
    # Si es ruta relativa, hacerla relativa al directorio base
    if not os.path.isabs(path):
        base_dir = get_base_directory()
        path = os.path.join(base_dir, path)
    
    os.makedirs(path, exist_ok=True)
    return path


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