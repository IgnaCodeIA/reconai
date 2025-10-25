import mediapipe as mp
import cv2
from core.utils import log_info, log_error


class PoseDetector:
    """
    Clase encargada de inicializar y ejecutar MediaPipe Pose
    para la detección de puntos articulares (landmarks) en imágenes o vídeo.
    """

    def __init__(self, min_detection_confidence=0.5, min_tracking_confidence=0.5):
        self.mp_pose = mp.solutions.pose
        self.pose = self.mp_pose.Pose(
            min_detection_confidence=min_detection_confidence,
            min_tracking_confidence=min_tracking_confidence
        )
        self.mp_drawing = mp.solutions.drawing_utils
        log_info("PoseDetector inicializado correctamente con MediaPipe Pose.")

    def process_frame(self, frame):
        """
        Procesa un frame con MediaPipe Pose y devuelve los resultados.

        Parámetros:
        -----------
        frame : np.ndarray
            Imagen en formato BGR (como la devuelve OpenCV).

        Retorna:
        --------
        tuple[np.ndarray, mediapipe.python.solutions.pose.PoseLandmarks or None]
            (imagen procesada BGR, resultados de MediaPipe o None si hay error)
        """
        try:
            image_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            image_rgb.flags.writeable = False
            results = self.pose.process(image_rgb)
            image_rgb.flags.writeable = True
            image_bgr = cv2.cvtColor(image_rgb, cv2.COLOR_RGB2BGR)
            return image_bgr, results
        except Exception as e:
            log_error(f"Error procesando frame: {e}")
            return frame, None

    def draw_landmarks(self, image, results):
        """
        Dibuja los landmarks y las conexiones del cuerpo sobre la imagen.

        Parámetros:
        -----------
        image : np.ndarray
            Imagen en formato BGR.
        results : mediapipe.framework.formats.landmark_pb2.NormalizedLandmarkList
            Resultado de MediaPipe Pose.
        """
        if results and results.pose_landmarks:
            self.mp_drawing.draw_landmarks(
                image,
                results.pose_landmarks,
                self.mp_pose.POSE_CONNECTIONS,
                landmark_drawing_spec=self.mp_drawing.DrawingSpec(color=(0, 0, 255), thickness=2, circle_radius=2),
                connection_drawing_spec=self.mp_drawing.DrawingSpec(color=(0, 255, 0), thickness=2)
            )
        return image

    def extract_landmarks(self, results):
        """
        Extrae las coordenadas (x, y, z, visibility) de todos los landmarks detectados.

        Parámetros:
        -----------
        results : mediapipe.python.solutions.pose.PoseLandmarks

        Retorna:
        --------
        dict[str, tuple]
            Diccionario con los nombres de los landmarks y sus coordenadas.
        """
        if not results or not results.pose_landmarks:
            return {}

        landmarks = {}
        for idx, lm in enumerate(results.pose_landmarks.landmark):
            name = self.mp_pose.PoseLandmark(idx).name
            landmarks[name] = (lm.x, lm.y, lm.z, lm.visibility)
        return landmarks

    def release(self):
        """Libera los recursos del modelo de MediaPipe."""
        self.pose.close()
