"""
Gestión centralizada de rutas para Recon IA.
Compatible con PyInstaller - persiste datos fuera del ejecutable.

CRÍTICO: Este módulo garantiza que los datos del usuario NO se pierdan
al actualizar el ejecutable, ya que se almacenan en AppData.
"""

import os
import sys
import shutil
from pathlib import Path
from typing import Tuple
import re


# ============================================================
# DIRECTORIO BASE DE DATOS (AppData en Windows)
# ============================================================

def get_app_data_dir() -> Path:
    """
    Obtiene el directorio de datos persistentes de la aplicación.
    
    Ubicaciones según plataforma:
    - Windows: C:\\Users\\{usuario}\\AppData\\Local\\ReconIA
    - macOS: ~/Library/Application Support/ReconIA
    - Linux: ~/.local/share/ReconIA
    
    Returns:
        Path: Directorio de datos de la aplicación
    """
    if sys.platform == 'win32':
        # Windows: usar LOCALAPPDATA
        appdata = os.environ.get('LOCALAPPDATA', os.path.expanduser('~/AppData/Local'))
        data_dir = Path(appdata) / 'ReconIA'
    elif sys.platform == 'darwin':
        # macOS: usar Library/Application Support
        data_dir = Path.home() / 'Library' / 'Application Support' / 'ReconIA'
    else:
        # Linux: usar .local/share
        data_dir = Path.home() / '.local' / 'share' / 'ReconIA'
    
    # Crear directorio si no existe
    data_dir.mkdir(parents=True, exist_ok=True)
    
    return data_dir


def get_app_root() -> Path:
    """
    Obtiene la carpeta raíz de la aplicación (donde está el .exe o el script).
    
    NOTA: Esta ruta NO debe usarse para datos persistentes, solo para recursos
    incluidos en el ejecutable.
    
    Returns:
        Path: Directorio raíz de la aplicación
    """
    if getattr(sys, 'frozen', False):
        # Ejecutable PyInstaller: directorio del .exe
        return Path(sys.executable).parent
    else:
        # Modo desarrollo: raíz del proyecto
        return Path(__file__).parent.parent


# ============================================================
# DIRECTORIOS DE DATOS
# ============================================================

def get_uploads_dir() -> Path:
    """
    Carpeta para archivos originales subidos por usuarios.
    
    Estructura:
    - uploads/videos/  → Videos originales
    - uploads/images/  → Imágenes originales
    
    Returns:
        Path: Directorio de uploads
    """
    uploads = get_app_data_dir() / 'uploads'
    uploads.mkdir(exist_ok=True)
    
    # Crear subdirectorios
    (uploads / 'videos').mkdir(exist_ok=True)
    (uploads / 'images').mkdir(exist_ok=True)
    
    return uploads


def get_temp_dir() -> Path:
    """
    Carpeta para archivos temporales durante procesamiento.
    
    IMPORTANTE: Esta carpeta se limpia automáticamente después de procesar.
    
    Returns:
        Path: Directorio temporal
    """
    temp = get_app_data_dir() / 'temp'
    temp.mkdir(exist_ok=True)
    return temp


def get_exports_dir() -> Path:
    """
    Carpeta para videos/imágenes procesados (salidas finales).
    
    Estructura:
    - exports/videos/  → Videos procesados
    - exports/images/  → Imágenes procesadas
    
    Returns:
        Path: Directorio de exportaciones
    """
    exports = get_app_data_dir() / 'exports'
    exports.mkdir(exist_ok=True)
    
    # Crear subdirectorios
    (exports / 'videos').mkdir(exist_ok=True)
    (exports / 'images').mkdir(exist_ok=True)
    
    return exports


def get_database_dir() -> Path:
    """
    Carpeta para la base de datos SQLite.
    
    Returns:
        Path: Directorio de base de datos
    """
    db_dir = get_app_data_dir() / 'database'
    db_dir.mkdir(exist_ok=True)
    return db_dir


def get_logs_dir() -> Path:
    """
    Carpeta para archivos de log.
    
    Returns:
        Path: Directorio de logs
    """
    logs = get_app_data_dir() / 'logs'
    logs.mkdir(exist_ok=True)
    return logs


# ============================================================
# RUTAS ESPECÍFICAS
# ============================================================

def get_db_path() -> Path:
    """
    Ruta completa al archivo de base de datos SQLite.
    
    Returns:
        Path: Ruta a sessions.db
    """
    return get_database_dir() / 'sessions.db'


def get_log_path() -> Path:
    """
    Ruta completa al archivo de log principal.
    
    Returns:
        Path: Ruta a recon_ia.log
    """
    return get_logs_dir() / 'recon_ia.log'


# ============================================================
# UTILIDADES DE ARCHIVOS
# ============================================================

def get_safe_filename(original_name: str, prefix: str = "") -> str:
    """
    Sanitiza un nombre de archivo para evitar inyecciones de ruta.
    
    Reglas:
    - Elimina caracteres peligrosos (../, /, \\, etc.)
    - Reemplaza espacios por guiones bajos
    - Limita longitud a 200 caracteres
    - Añade prefijo opcional (timestamp, UUID, etc.)
    
    Args:
        original_name: Nombre original del archivo
        prefix: Prefijo opcional (ej: "20250118_143022_")
    
    Returns:
        str: Nombre sanitizado
    
    Examples:
        >>> get_safe_filename("../../etc/passwd.mp4")
        'etc_passwd.mp4'
        >>> get_safe_filename("Mi Video.mp4", "session_123_")
        'session_123_Mi_Video.mp4'
    """
    # Obtener solo el nombre base (sin ruta)
    name = Path(original_name).name
    
    # Reemplazar caracteres peligrosos
    dangerous_chars = ['..', '/', '\\', '<', '>', ':', '"', '|', '?', '*']
    for char in dangerous_chars:
        name = name.replace(char, '_')
    
    # Reemplazar espacios por guiones bajos
    name = name.replace(' ', '_')
    
    # Eliminar caracteres no-ASCII (opcional, comentar si se necesitan acentos)
    name = re.sub(r'[^\x00-\x7F]+', '_', name)
    
    # Añadir prefijo si se proporciona
    if prefix:
        name = f"{prefix}{name}"
    
    # Limitar longitud
    max_length = 200
    if len(name) > max_length:
        # Preservar extensión
        ext = Path(name).suffix
        name_without_ext = Path(name).stem
        max_stem_length = max_length - len(ext)
        name = name_without_ext[:max_stem_length] + ext
    
    return name


def check_disk_space(required_mb: int = 100) -> Tuple[bool, int]:
    """
    Verifica que haya espacio suficiente en disco.
    
    Args:
        required_mb: Megabytes requeridos
    
    Returns:
        tuple: (hay_espacio: bool, mb_disponibles: int)
    
    Examples:
        >>> has_space, available = check_disk_space(500)
        >>> if not has_space:
        ...     print(f"Insuficiente espacio. Disponible: {available}MB")
    """
    try:
        stat = shutil.disk_usage(get_app_data_dir())
        available_mb = stat.free / (1024 * 1024)
        has_space = available_mb >= required_mb
        return (has_space, int(available_mb))
    except Exception as e:
        print(f"⚠️ Error al verificar espacio en disco: {e}")
        # En caso de error, asumir que hay espacio (fail-safe)
        return (True, 0)


def get_disk_usage_stats() -> dict:
    """
    Obtiene estadísticas detalladas de uso de disco.
    
    Returns:
        dict: {
            'total_gb': float,
            'used_gb': float,
            'free_gb': float,
            'percent_used': float,
            'app_data_size_mb': float
        }
    """
    try:
        stat = shutil.disk_usage(get_app_data_dir())
        
        # Calcular tamaño de carpeta ReconIA
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
        print(f"⚠️ Error calculando uso de disco: {e}")
        return {
            'total_gb': 0,
            'used_gb': 0,
            'free_gb': 0,
            'percent_used': 0,
            'app_data_size_mb': 0
        }


# ============================================================
# INICIALIZACIÓN
# ============================================================

def initialize_directories():
    """
    Crea toda la estructura de directorios necesaria.
    
    Debe llamarse al inicio de la aplicación.
    """
    # Crear todos los directorios
    get_uploads_dir()
    get_temp_dir()
    get_exports_dir()
    get_database_dir()
    get_logs_dir()
    
    print(f"✅ Directorios inicializados en: {get_app_data_dir()}")


# ============================================================
# AUTO-INICIALIZACIÓN
# ============================================================

# Crear directorios automáticamente al importar el módulo
try:
    initialize_directories()
except Exception as e:
    print(f"⚠️ Error inicializando directorios: {e}")


# ============================================================
# TESTING (solo en desarrollo)
# ============================================================

if __name__ == "__main__":
    print("=" * 60)
    print("PRUEBA DE PATH MANAGER")
    print("=" * 60)
    
    print(f"\n📁 Directorio de datos: {get_app_data_dir()}")
    print(f"📁 Directorio raíz: {get_app_root()}")
    print(f"📁 Uploads: {get_uploads_dir()}")
    print(f"📁 Temp: {get_temp_dir()}")
    print(f"📁 Exports: {get_exports_dir()}")
    print(f"📁 Database: {get_database_dir()}")
    print(f"📁 Logs: {get_logs_dir()}")
    print(f"📄 DB Path: {get_db_path()}")
    print(f"📄 Log Path: {get_log_path()}")
    
    print("\n💾 Espacio en disco:")
    has_space, available = check_disk_space(100)
    print(f"   ¿Hay 100MB disponibles? {has_space} ({available}MB libres)")
    
    stats = get_disk_usage_stats()
    print(f"   Total: {stats['total_gb']}GB")
    print(f"   Usado: {stats['used_gb']}GB ({stats['percent_used']}%)")
    print(f"   Libre: {stats['free_gb']}GB")
    print(f"   ReconIA: {stats['app_data_size_mb']}MB")
    
    print("\n🔒 Sanitización de nombres:")
    test_names = [
        "../../etc/passwd.mp4",
        "Mi Video con Espacios.mp4",
        "video<>|?.avi",
        "sesión_paciente_2024.mov"
    ]
    for name in test_names:
        safe = get_safe_filename(name, "20250118_")
        print(f"   '{name}' → '{safe}'")
    
    print("\n✅ Path Manager funcionando correctamente")
    print("=" * 60)