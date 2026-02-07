import cv2
import mediapipe as mp
import numpy as np
from typing import Dict, Tuple, Any

class PoseDetector:
    
    def __init__(
        self,
        static_image_mode: bool = False,
        model_complexity: int = 1,
        smooth_landmarks: bool = True,
        min_detection_confidence: float = 0.5,
        min_tracking_confidence: float = 0.5
    ):
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
        frame_rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
        results = self.pose.process(frame_rgb)
        return frame_bgr, results
    
    def extract_landmarks(self, results) -> Dict[str, Tuple[float, float, float, float]]:
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
        if results and results.pose_landmarks:
            self.mp_drawing.draw_landmarks(
                image,
                results.pose_landmarks,
                self.mp_pose.POSE_CONNECTIONS
            )
        
        if sequence is not None:
            self._draw_sequence_overlay(image, sequence)
        
        return image
    
    def draw_mediapipe_full_overlay(self, image, results, sequence: int = None) -> Any:
        if results and results.pose_landmarks:
            self.mp_drawing.draw_landmarks(
                image,
                results.pose_landmarks,
                self.mp_pose.POSE_CONNECTIONS,
                landmark_drawing_spec=self.mp_drawing_styles.get_default_pose_landmarks_style(),
                connection_drawing_spec=self.mp_drawing.DrawingSpec(
                    color=(0, 255, 0),
                    thickness=2,
                    circle_radius=2
                )
            )
        
        if sequence is not None:
            self._draw_sequence_overlay(image, sequence)
        
        return image
    
    def draw_mediapipe_on_white_background(self, width: int, height: int, results, sequence: int = None) -> Any:
        white_background = np.ones((height, width, 3), dtype=np.uint8) * 255
        
        if results and results.pose_landmarks:
            self.mp_drawing.draw_landmarks(
                white_background,
                results.pose_landmarks,
                self.mp_pose.POSE_CONNECTIONS,
                landmark_drawing_spec=self.mp_drawing_styles.get_default_pose_landmarks_style(),
                connection_drawing_spec=self.mp_drawing.DrawingSpec(
                    color=(0, 255, 0),
                    thickness=2,
                    circle_radius=2
                )
            )
        
        if sequence is not None:
            self._draw_sequence_overlay(white_background, sequence)
        
        return white_background
    
    def _draw_sequence_overlay(self, image, sequence: int) -> None:
        cv2.rectangle(image, (15, 5), (250, 40), (250, 250, 250), -1)
        cv2.putText(
            image, 
            f'Secuencia: {sequence}', 
            (20, 30), 
            cv2.FONT_HERSHEY_SIMPLEX, 
            1,
            (255, 0, 0),
            1,
            cv2.LINE_AA
        )
    
    def release(self):
        if hasattr(self, 'pose') and self.pose:
            self.pose.close()