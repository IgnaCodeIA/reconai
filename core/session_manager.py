import csv
import os
import time
import cv2

from core.utils import ensure_dir, timestamp
from db import crud  # integración con la base de datos


class SessionManager:
    """
    Gestiona la sesión de captura y análisis:
    - Crea y escribe en un archivo CSV con datos biomecánicos.
    - Gestiona el vídeo de salida con anotaciones.
    - Registra automáticamente la sesión y sus métricas en la base de datos.
    """

    def __init__(self, output_dir="data/exports", base_name="session", patient_id=None, exercise_id=None):
        self.output_dir = ensure_dir(output_dir)
        self.csv_file = None
        self.csv_writer = None
        self.video_writer = None
        self.start_time = None
        self.frame_size = None
        self.fps = None
        self.base_name = base_name
        self.patient_id = patient_id
        self.exercise_id = exercise_id
        self.session_id = None

        # variables internas para calcular métricas básicas
        self.angle_records = {}

    def start_csv(self, headers):
        """Crea el archivo CSV con los encabezados indicados."""
        ts = timestamp()
        self.csv_path = os.path.join(self.output_dir, f"{self.base_name}_{ts}.csv")
        self.csv_file = open(self.csv_path, "w", newline="")
        self.csv_writer = csv.writer(self.csv_file)
        self.csv_writer.writerow(headers)
        self.start_time = time.time()
        print(f"[SessionManager] CSV creado en {self.csv_path}")
        return self.csv_path

    def start_video(self, width, height, fps):
        """Configura el VideoWriter para grabar el vídeo con anotaciones."""
        self.frame_size = (width, height)
        self.fps = round(fps)
        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        ts = timestamp()
        self.video_path = os.path.join(self.output_dir, f"{self.base_name}_{ts}.mp4")
        self.video_writer = cv2.VideoWriter(self.video_path, fourcc, self.fps, self.frame_size)
        print(f"[SessionManager] Grabación de vídeo iniciada en {self.video_path}")
        return self.video_path

    def write_csv_row(self, row):
        """Escribe una fila en el CSV (por ejemplo, ángulos, coordenadas...)."""
        if self.csv_writer:
            self.csv_writer.writerow(row)

    def record_angle(self, joint_name, angle_value):
        """Guarda temporalmente valores de ángulo para calcular métricas."""
        if joint_name not in self.angle_records:
            self.angle_records[joint_name] = []
        self.angle_records[joint_name].append(angle_value)

    def write_video_frame(self, frame):
        """Añade un frame procesado al vídeo de salida."""
        if self.video_writer:
            self.video_writer.write(frame)

    def close_session(self):
        """Cierra archivos, los renombra y registra la sesión y métricas en la base de datos."""
        if self.csv_file:
            self.csv_file.close()

        if self.video_writer:
            self.video_writer.release()

        if self.frame_size and self.fps:
            w, h = self.frame_size
            ts = timestamp()
            new_csv_name = f"{self.base_name}_{w}x{h}_{self.fps}_{ts}.csv"
            new_video_name = f"{self.base_name}_{w}x{h}_{self.fps}_{ts}.mp4"

            new_csv_path = os.path.join(self.output_dir, new_csv_name)
            new_video_path = os.path.join(self.output_dir, new_video_name)

            try:
                os.rename(self.csv_path, new_csv_path)
                os.rename(self.video_path, new_video_path)
                self.csv_path = new_csv_path
                self.video_path = new_video_path
                print(f"[SessionManager] Archivos renombrados:")
                print(f"  - CSV  → {new_csv_path}")
                print(f"  - MP4  → {new_video_path}")
            except Exception as e:
                print(f"[SessionManager] Error al renombrar archivos: {e}")

        # Registro en base de datos
        if self.patient_id:
            self.session_id = crud.create_session(
                patient_id=self.patient_id,
                exercise_id=self.exercise_id,
                csv_path=self.csv_path,
                video_path=self.video_path
            )
            print(f"[SessionManager] Sesión registrada en BD con id {self.session_id}")

        # Guardar métricas básicas
        for joint, values in self.angle_records.items():
            if values:
                max_angle = max(values)
                min_angle = min(values)
                range_angle = max_angle - min_angle
                crud.add_metric(self.session_id, f"{joint}_angulo_max", max_angle)
                crud.add_metric(self.session_id, f"{joint}_angulo_min", min_angle)
                crud.add_metric(self.session_id, f"{joint}_rango", range_angle)

        print("[SessionManager] Sesión finalizada correctamente.")

    def elapsed_time(self):
        """Devuelve el tiempo (en segundos) desde que comenzó la sesión."""
        if self.start_time:
            return round(time.time() - self.start_time, 2)
        return 0
