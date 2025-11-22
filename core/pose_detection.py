# core/pose_detection.py
"""
Wrapper para MediaPipe Pose detection.
Gestiona detección de landmarks y rendering de overlays.

NUEVO: Soporte para overlay MediaPipe completo (33 landmarks + conexiones estándar)
NUEVO: Contador de secuencia visible en overlays (estilo Phiteca)
NUEVO: Overlay MediaPipe sobre fondo blanco puro (sin video original)
"""

import cv2
import mediapipe as mp
import numpy as np
from typing import Dict, Tuple, Any


class PoseDetector:
    """
    Detector de pose usando MediaPipe.
    
    Funcionalidades:
    - Detección de 33 landmarks corporales
    - Extracción de coordenadas normalizadas
    - Overlay estándar de MediaPipe (completo)
    - Overlay MediaPipe sobre fondo blanco puro (NUEVO)
    - Overlay personalizado (legacy - en legacy_overlay.py)
    - Contador de secuencia en overlays
    """
    
    def __init__(
        self,
        static_image_mode: bool = False,
        model_complexity: int = 1,
        smooth_landmarks: bool = True,
        min_detection_confidence: float = 0.5,
        min_tracking_confidence: float = 0.5
    ):
        """
        Inicializa el detector de pose.
        
        Args:
            static_image_mode: Si True, trata cada imagen independientemente
            model_complexity: 0 (ligero), 1 (normal), 2 (pesado)
            smooth_landmarks: Suavizado temporal de landmarks
            min_detection_confidence: Umbral mínimo de detección
            min_tracking_confidence: Umbral mínimo de tracking
        """
        self.mp_pose = mp.solutions.pose
        self.mp_drawing = mp.solutions.drawing_utils
        self.mp_drawing_styles = mp.solutions.drawing_styles
        
        self.pose = self.mp_pose.Pose(
            static_image_mode=static_image_mode,
            model_complexity=model_complexity,
            smooth_landmarks=smooth_landmarks,
            min_detection_confidence=min_detection_confidence,
            min_tracking_confidence=min_tracking_confidence
        )
    
    def process_frame(self, frame_bgr) -> Tuple[Any, Any]:
        """
        Procesa un frame BGR y detecta pose.
        
        Args:
            frame_bgr: Frame en formato BGR (OpenCV)
        
        Returns:
            Tupla (frame_bgr, results)
            - frame_bgr: El mismo frame de entrada (sin modificar)
            - results: Resultados de MediaPipe con pose_landmarks
        """
        # MediaPipe requiere RGB
        frame_rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
        
        # Procesamiento
        results = self.pose.process(frame_rgb)
        
        return frame_bgr, results
    
    def extract_landmarks(self, results) -> Dict[str, Tuple[float, float, float, float]]:
        """
        Extrae landmarks en formato de diccionario.
        
        Args:
            results: Resultados de MediaPipe
        
        Returns:
            Diccionario {nombre_landmark: (x, y, z, visibility)}
            Coordenadas normalizadas [0..1]
        """
        if not results or not results.pose_landmarks:
            return {}
        
        landmarks_dict = {}
        for idx, landmark in enumerate(results.pose_landmarks.landmark):
            landmark_name = self.mp_pose.PoseLandmark(idx).name
            landmarks_dict[landmark_name] = (
                landmark.x,
                landmark.y,
                landmark.z,
                landmark.visibility
            )
        
        return landmarks_dict
    
    def draw_landmarks(self, image, results, sequence: int = None) -> Any:
        """
        Dibuja landmarks básicos sobre la imagen (versión simple).
        
        DEPRECADO: Usar draw_mediapipe_full_overlay() para overlay completo.
        
        Args:
            image: Frame BGR
            results: Resultados de MediaPipe
            sequence: Número de secuencia actual (opcional)
        
        Returns:
            Imagen con landmarks dibujados
        """
        if results and results.pose_landmarks:
            self.mp_drawing.draw_landmarks(
                image,
                results.pose_landmarks,
                self.mp_pose.POSE_CONNECTIONS
            )
        
        # NUEVO: Dibujar contador de secuencia (estilo Phiteca)
        if sequence is not None:
            self._draw_sequence_overlay(image, sequence)
        
        return image
    
    def draw_mediapipe_full_overlay(self, image, results, sequence: int = None) -> Any:
        """
        Dibuja el overlay COMPLETO de MediaPipe con estilo estándar.
        
        Incluye:
        - 33 landmarks con círculos
        - Conexiones entre landmarks (esqueleto completo)
        - Estilo de colores estándar de MediaPipe
        - Contador de secuencia (NUEVO)
        
        Args:
            image: Frame BGR (se modifica in-place)
            results: Resultados de MediaPipe
            sequence: Número de secuencia actual (opcional)
        
        Returns:
            Imagen con overlay completo de MediaPipe
        """
        if results and results.pose_landmarks:
            # Dibujar landmarks + conexiones con estilo completo
            self.mp_drawing.draw_landmarks(
                image,
                results.pose_landmarks,
                self.mp_pose.POSE_CONNECTIONS,
                landmark_drawing_spec=self.mp_drawing_styles.get_default_pose_landmarks_style(),
                connection_drawing_spec=self.mp_drawing.DrawingSpec(
                    color=(0, 255, 0),  # Verde
                    thickness=2,
                    circle_radius=2
                )
            )
        
        # NUEVO: Dibujar contador de secuencia (estilo Phiteca)
        if sequence is not None:
            self._draw_sequence_overlay(image, sequence)
        
        return image
    
    def draw_mediapipe_on_white_background(self, width: int, height: int, results, sequence: int = None) -> Any:
        """
        ⚪ NUEVO: Dibuja el esqueleto de MediaPipe sobre un FONDO BLANCO PURO.
        
        Genera una imagen blanca y dibuja solo los landmarks y conexiones,
        sin el video original de fondo. Ideal para análisis biomecánico donde
        solo importa la estructura del esqueleto.
        
        Args:
            width: Ancho del frame
            height: Alto del frame
            results: Resultados de MediaPipe
            sequence: Número de secuencia actual (opcional)
        
        Returns:
            Imagen con fondo blanco y esqueleto de pose dibujado
        """
        # Crear imagen blanca (255, 255, 255) = blanco en BGR
        white_background = np.ones((height, width, 3), dtype=np.uint8) * 255
        
        if results and results.pose_landmarks:
            # Dibujar landmarks + conexiones con estilo completo sobre el fondo blanco
            self.mp_drawing.draw_landmarks(
                white_background,
                results.pose_landmarks,
                self.mp_pose.POSE_CONNECTIONS,
                landmark_drawing_spec=self.mp_drawing_styles.get_default_pose_landmarks_style(),
                connection_drawing_spec=self.mp_drawing.DrawingSpec(
                    color=(0, 255, 0),  # Verde para las conexiones
                    thickness=2,
                    circle_radius=2
                )
            )
        
        # Dibujar contador de secuencia (estilo Phiteca)
        if sequence is not None:
            self._draw_sequence_overlay(white_background, sequence)
        
        return white_background
    
    def _draw_sequence_overlay(self, image, sequence: int) -> None:
        """
        Dibuja el contador de secuencia en la esquina superior izquierda.
        Estilo Phiteca: rectángulo blanco + texto azul.
        
        Args:
            image: Frame BGR donde dibujar (se modifica in-place)
            sequence: Número de secuencia actual
        """
        # Rectángulo blanco de fondo (estilo original)
        cv2.rectangle(image, (15, 5), (250, 40), (250, 250, 250), -1)
        
        # Texto "Secuencia: X" en azul (BGR = 255, 0, 0)
        cv2.putText(
            image, 
            f'Secuencia: {sequence}', 
            (20, 30), 
            cv2.FONT_HERSHEY_SIMPLEX, 
            1,           # font_scale
            (255, 0, 0), # color azul en BGR
            1,           # thickness
            cv2.LINE_AA
        )
    
    def release(self):
        """Libera recursos de MediaPipe."""
        if hasattr(self, 'pose') and self.pose:
            self.pose.close()