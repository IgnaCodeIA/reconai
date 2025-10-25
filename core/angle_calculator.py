import numpy as np


from core.utils import safe_round


def calculate_angle(a, b, c):
    """
    Calcula el ángulo (en grados) formado por tres puntos A-B-C.

    Parámetros:
    -----------
    a, b, c : list o tuple de dos elementos
        Coordenadas (x, y) de los puntos A, B y C.
        El punto 'b' es el vértice del ángulo.

    Retorna:
    --------
    float
        Ángulo en grados entre los segmentos BA y BC.

    Notas:
    ------
    - El resultado está en el rango [0, 180].
    - Si alguno de los puntos es inválido (None o contiene NaN),
      devuelve None.
    """

    try:
        # Convertir a arrays NumPy
        a = np.array(a, dtype=float)
        b = np.array(b, dtype=float)
        c = np.array(c, dtype=float)

        # Vectores
        ba = a - b
        bc = c - b

        # Normalizar (evita divisiones por cero)
        norm_ba = np.linalg.norm(ba)
        norm_bc = np.linalg.norm(bc)
        if norm_ba == 0 or norm_bc == 0:
            return None

        # Calcular coseno del ángulo
        cosine_angle = np.dot(ba, bc) / (norm_ba * norm_bc)

        # Evitar errores por precisión numérica
        cosine_angle = np.clip(cosine_angle, -1.0, 1.0)

        # Convertir a grados
        angle = np.degrees(np.arccos(cosine_angle))
        return safe_round(abs(angle))


    except Exception as e:
        print(f"[calculate_angle] Error al calcular ángulo: {e}")
        return None
