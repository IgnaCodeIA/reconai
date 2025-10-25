import os
import time
import datetime


def ensure_dir(path):
    """
    Crea el directorio si no existe.
    """
    if not os.path.exists(path):
        os.makedirs(path)
        print(f"[Utils] Directorio creado: {path}")
    return path


def timestamp():
    """
    Devuelve un timestamp legible para logs o nombres de archivo.
    Ejemplo: '2025-10-25_15-30-12'
    """
    return datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")


def current_time_seconds():
    """
    Devuelve el tiempo actual en segundos (float), útil para medidas de duración.
    """
    return time.time()


def elapsed_time(start_time):
    """
    Devuelve el tiempo transcurrido desde `start_time` en segundos (float).
    """
    return round(time.time() - start_time, 2)



def log_info(message):
    print(f"[INFO] {message}")

def log_warn(message):
    print(f"[WARN] {message}")

def log_error(message):
    print(f"[ERROR] {message}")



def clamp(value, min_value, max_value):
    """
    Restringe un valor dentro del rango [min_value, max_value].
    """
    return max(min(value, max_value), min_value)


def safe_round(value, decimals=2):
    """
    Redondea de forma segura, devolviendo 0.0 si no es numérico.
    """
    try:
        return round(float(value), decimals)
    except (TypeError, ValueError):
        return 0.0
