import logging
import sys

from core.path_manager import get_log_path

def get_logger(name: str = "reconia"):
    """Return a configured logger that writes DEBUG to file and INFO to stdout."""
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
        # If the disk log cannot be opened, fall back to stdout-only logging.
        pass

    logger.addHandler(ch)
    logger.propagate = False
    return logger