# core/session_manager.py
import os
import time
import math
import cv2
from typing import Dict, List

from core.utils import ensure_dir, timestamp
from db import crud
from core.logger import get_logger

log = get_logger("core.session")


class SessionManager:
    """
    Gestiona una sesión de captura/análisis:
    - Inicializa salida de vídeo y fila en BD (sessions).
    - Registra datos por frame en movement_data.
    - Agrega métricas al cerrar (min, max, range de ángulos).
    
    NUEVO: Sampling rate configurable para reducir volumen de datos.
    """

    def __init__(
        self,
        output_dir: str = "data/exports",
        base_name: str = "session",
        patient_id: int | None = None,
        exercise_id: int | None = None,
        notes: str | None = None,
        sampling_rate: float = 0.0,  # NUEVO: 0 = todos los frames, >0 = intervalo en segundos
    ):
        self.output_dir = ensure_dir(output_dir)
        self.video_writer: cv2.VideoWriter | None = None
        self.start_time: float | None = None
        self.frame_size: tuple[int, int] | None = None
        self.fps: int | None = None
        self.base_name = base_name
        self.patient_id = patient_id
        self.exercise_id = exercise_id
        self.session_id: int | None = None
        self.notes = notes
        self.video_path: str | None = None
        
        # NUEVO: Control de sampling
        self.sampling_rate = sampling_rate
        self.last_sample_time = 0.0

        # Acumulador de ángulos para métricas
        self.angle_records: Dict[str, List[float]] = {}

        # Contador de frames escritos a vídeo
        self._frames_written = 0
        self._frames_recorded_to_db = 0  # NUEVO: contador de frames guardados en BD

        log.info(
            "SessionManager created base_name=%s, patient=%s, exercise=%s, sampling_rate=%s",
            self.base_name, self.patient_id, self.exercise_id, self.sampling_rate
        )

    # ============================================================
    # INICIALIZACIÓN
    # ============================================================

    def start_session(self, width: int, height: int, fps: float | int) -> int:
        """
        Crea writer de vídeo y la fila de sesión en BD.
        Devuelve el session_id.
        """
        self.frame_size = (width, height)
        self.fps = int(round(fps)) if fps else 30
        self.start_time = time.time()

        ts = timestamp()
        self.video_path = os.path.join(
            self.output_dir, f"{self.base_name}_{width}x{height}_{self.fps}_{ts}.mp4"
        )

        # Writer de vídeo
        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        self.video_writer = cv2.VideoWriter(self.video_path, fourcc, self.fps, self.frame_size)
        if not self.video_writer or not self.video_writer.isOpened():
            log.warning("VideoWriter no está abierto tras start_session()")

        # Fila en BD
        log.info(
            "start_session: video=%s, size=%s, fps=%s, patient=%s, exercise=%s",
            self.video_path, self.frame_size, self.fps, self.patient_id, self.exercise_id
        )
        self.session_id = crud.create_session(
            patient_id=self.patient_id,
            exercise_id=self.exercise_id,
            video_path=self.video_path,
            notes=self.notes
        )
        log.info("start_session OK: session_id=%s", self.session_id)
        return int(self.session_id)

    # ============================================================
    # REGISTRO POR FRAME
    # ============================================================

    def should_record_frame(self) -> bool:
        """
        Determina si este frame debe guardarse en BD según sampling_rate.
        
        Returns:
            True si debe guardarse, False si debe saltarse.
        """
        if self.sampling_rate <= 0:
            return True  # Todos los frames
        
        elapsed = self.elapsed_time()
        if elapsed - self.last_sample_time >= self.sampling_rate:
            self.last_sample_time = elapsed
            return True
        return False

    def record_frame_data(self, frame_index: int, elapsed_time: float, joints: dict) -> None:
        """
        Guarda datos biomecánicos del frame en movement_data y
        acumula ángulos para métricas.
        
        NUEVO: Solo guarda si should_record_frame() == True
        """
        if self.session_id is None:
            log.error("record_frame_data llamado con session_id=None")
            raise RuntimeError("Session must be started before recording data.")

        # NUEVO: Verificar sampling rate
        if not self.should_record_frame():
            # Acumular ángulos pero NO guardar en BD
            self._accumulate_angles(joints)
            return

        data = {
            "time_seconds": elapsed_time,
            "frame": frame_index,
            **joints
        }

        # Inserta movimiento
        try:
            crud.add_movement_data(self.session_id, data)
            self._frames_recorded_to_db += 1
        except Exception:
            # En producción preferimos no interrumpir la sesión por un fallo puntual
            log.exception("add_movement_data FAILED")

        # Acumula ángulos
        self._accumulate_angles(joints)

    def _accumulate_angles(self, joints: dict) -> None:
        """Acumula ángulos para cálculo de métricas (separado para reutilización)"""
        for key, val in joints.items():
            if "angle" in key and val is not None:
                try:
                    fval = float(val)
                    if not math.isnan(fval):
                        self.angle_records.setdefault(key, []).append(fval)
                except (TypeError, ValueError):
                    pass

    def write_video_frame(self, frame) -> None:
        """Escribe un frame al vídeo de salida (si hay writer)."""
        if self.video_writer:
            self.video_writer.write(frame)
            self._frames_written += 1
        else:
            log.warning("write_video_frame llamado sin video_writer inicializado")

    # ============================================================
    # CIERRE DE SESIÓN
    # ============================================================

    def close_session(self) -> None:
        """
        Libera recursos y calcula/guarda métricas agregadas.
        """
        log.info(
            "close_session ENTER sid=%s, frames_written=%s, frames_in_db=%s, sampling_rate=%s",
            self.session_id, self._frames_written, self._frames_recorded_to_db, self.sampling_rate
        )

        if self.video_writer:
            try:
                self.video_writer.release()
            except Exception:
                log.exception("close_session: video_writer.release() FAILED")

        if not self.session_id:
            log.warning("close_session: session_id is None (no se guardarán métricas).")
            return

        if not self.angle_records:
            log.info("close_session: sin registros de ángulos para sid=%s", self.session_id)
            log.info(
                "close_session DONE: sid=%s, metrics_rows_saved=0, video=%s, frames_written=%s",
                self.session_id, self.video_path, self._frames_written
            )
            return

        # Métricas clínicas agregadas
        saved = 0
        for metric_name, values in self.angle_records.items():
            if not values:
                continue

            # Sanea lista
            clean_vals: List[float] = []
            for v in values:
                try:
                    fv = float(v)
                    if not math.isnan(fv):
                        clean_vals.append(fv)
                except (TypeError, ValueError):
                    continue

            if not clean_vals:
                continue

            mx = max(clean_vals)
            mn = min(clean_vals)
            rg = mx - mn

            try:
                crud.add_metric(self.session_id, f"{metric_name}_max", mx, unit="degrees")
                crud.add_metric(self.session_id, f"{metric_name}_min", mn, unit="degrees")
                crud.add_metric(self.session_id, f"{metric_name}_range", rg, unit="degrees")
                saved += 3
            except Exception:
                log.exception("FAILED saving metrics for '%s'", metric_name)

        log.info(
            "close_session DONE: sid=%s, metrics_rows=%s, video=%s, frames_written=%s, frames_in_db=%s",
            self.session_id, saved, self.video_path, self._frames_written, self._frames_recorded_to_db
        )

    # ============================================================
    # UTILIDADES
    # ============================================================

    def elapsed_time(self) -> float:
        """Segundos transcurridos desde el inicio de la sesión."""
        if self.start_time:
            return round(time.time() - self.start_time, 2)
        return 0.0