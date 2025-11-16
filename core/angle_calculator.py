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

    Notes
    -----
    - The result is always in the range [0, 180].
    - Handles NaN and zero-length vectors safely.
    - This function assumes coordinates are normalized or within consistent units.

    Example
    -------
    >>> calculate_angle((0, 1), (0, 0), (1, 0))
    90.0
    """
    try:
        # Validate input
        if a is None or b is None or c is None:
            raise ValueError("Input points cannot be None.")

        # Convert to NumPy arrays (float precision)
        a, b, c = np.array(a, dtype=float), np.array(b, dtype=float), np.array(c, dtype=float)

        # Handle potential NaNs
        if np.isnan(a).any() or np.isnan(b).any() or np.isnan(c).any():
            raise ValueError("Input points contain NaN values.")

        # Compute vectors BA and BC
        ba = a - b
        bc = c - b

        # Compute magnitudes
        norm_ba = np.linalg.norm(ba)
        norm_bc = np.linalg.norm(bc)

        # Avoid division by zero
        if norm_ba == 0 or norm_bc == 0:
            return None

        # Compute cosine of the angle using the dot product formula
        cosine_angle = np.dot(ba, bc) / (norm_ba * norm_bc)

        # Clip to valid numerical range to prevent NaN from floating-point errors
        cosine_angle = np.clip(cosine_angle, -1.0, 1.0)

        # Compute the angle in degrees
        angle = np.degrees(np.arccos(cosine_angle))

        return safe_round(abs(angle))

    except Exception as e:
        print(f"[calculate_angle] Failed to compute angle: {e}")
        return None
