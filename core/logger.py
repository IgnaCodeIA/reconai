import logging
import sys

from core.path_manager import get_log_path

def get_logger(name: str = "reconia"):
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger

    logger.setLevel(logging.DEBUG)

    fmt = logging.Formatter('%(asctime)s %(levelname)s [%(name)s] %(message)s')

    ch = logging.StreamHandler(sys.stdout)
    ch.setLevel(logging.INFO)
    ch.setFormatter(fmt)

    try:
        log_path = get_log_path()
        fh = logging.FileHandler(str(log_path), encoding="utf-8")
        fh.setLevel(logging.DEBUG)
        fh.setFormatter(fmt)
        logger.addHandler(fh)
    except Exception:
        pass  # si no se puede escribir el log en disco, al menos sigue funcionando con stdout

    logger.addHandler(ch)
    logger.propagate = False
    return logger