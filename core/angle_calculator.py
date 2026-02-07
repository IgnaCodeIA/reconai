import numpy as np
from core.utils import safe_round


def calculate_angle(a, b, c):
    """
    Compute the angle (in degrees) formed by three 2D points A–B–C.

    Parameters
    ----------
    a : tuple[float, float]
        Coordinates (x, y) of the first point (A).
    b : tuple[float, float]
        Coordinates (x, y) of the vertex point (B).
    c : tuple[float, float]
        Coordinates (x, y) of the third point (C).

    Returns
    -------
    float or None
        The absolute angle in degrees between the segments BA and BC.
        Returns None if the input is invalid or the calculation fails.
    """
    try:
        if a is None or b is None or c is None:
            raise ValueError("Input points cannot be None.")

        a, b, c = np.array(a, dtype=float), np.array(b, dtype=float), np.array(c, dtype=float)

        if np.isnan(a).any() or np.isnan(b).any() or np.isnan(c).any():
            raise ValueError("Input points contain NaN values.")

        ba = a - b
        bc = c - b

        norm_ba = np.linalg.norm(ba)
        norm_bc = np.linalg.norm(bc)

        if norm_ba == 0 or norm_bc == 0:
            return None

        cosine_angle = np.dot(ba, bc) / (norm_ba * norm_bc)
        cosine_angle = np.clip(cosine_angle, -1.0, 1.0)
        angle = np.degrees(np.arccos(cosine_angle))

        return safe_round(abs(angle))

    except Exception as e:
        print(f"[calculate_angle] Failed to compute angle: {e}")
        return None