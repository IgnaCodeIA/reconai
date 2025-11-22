# core/session_manager.py
import os
import time
import math
import cv2
from typing import Dict, List, Tuple

from core.utils import ensure_dir, timestamp
from db import crud
from core.logger import get_logger

log = get_logger("core.session")


class SessionManager:
    """
    Gestiona una sesión de captura/análisis:
    - Inicializa hasta 3 salidas de vídeo (raw, mediapipe, legacy)
    - Registra datos por frame en movement_data
    - Agrega métricas al cerrar (min, max, range de ángulos y simetrías)
    
    NUEVO: 
    - Soporte para múltiples versiones de vídeo simultáneas
    - Sampling rate configurable para reducir volumen de datos
    - Métricas de simetría bilateral con unidades diferenciadas
    - Contador de secuencia visible en los 3 tipos de vídeo
    """

    def __init__(
        self,
        output_dir: str = "data/exports",
        base_name: str = "session",
        patient_id: int | None = None,
        exercise_id: int | None = None,
        notes: str | None = None,
        sampling_rate: float = 0.0,
        # NUEVO: Flags para controlar qué versiones generar
        generate_raw: bool = False,
        generate_mediapipe: bool = False,
        generate_legacy: bool = True,
    ):
        self.output_dir = ensure_dir(output_dir)
        
        # NUEVO: 3 VideoWriters (uno por cada versión)
        self.video_writer_raw: cv2.VideoWriter | None = None
        self.video_writer_mediapipe: cv2.VideoWriter | None = None
        self.video_writer_legacy: cv2.VideoWriter | None = None
        
        self.start_time: float | None = None
        self.frame_size: tuple[int, int] | None = None
        self.fps: int | None = None
        self.base_name = base_name
        self.patient_id = patient_id
        self.exercise_id = exercise_id
        self.session_id: int | None = None
        self.notes = notes
        
        # NUEVO: Rutas de los 3 vídeos
        self.video_path_raw: str | None = None
        self.video_path_mediapipe: str | None = None
        self.video_path_legacy: str | None = None
        
        # Control de sampling
        self.sampling_rate = sampling_rate
        self.last_sample_time = 0.0

        # Acumulador de métricas para agregación final
        self.metric_records: Dict[str, List[float]] = {}

        # Contadores
        self._frames_written = 0
        self._frames_recorded_to_db = 0
        
        # NUEVO: Contador de secuencia (estilo Phiteca)
        self.sequence_counter = 0
        
        # NUEVO: Flags de configuración
        self.generate_raw = generate_raw
        self.generate_mediapipe = generate_mediapipe
        self.generate_legacy = generate_legacy

        log.info(
            "SessionManager created base_name=%s, patient=%s, exercise=%s, sampling_rate=%s, "
            "versions=(raw=%s, mediapipe=%s, legacy=%s)",
            self.base_name, self.patient_id, self.exercise_id, self.sampling_rate,
            self.generate_raw, self.generate_mediapipe, self.generate_legacy
        )

    # ============================================================
    # INICIALIZACIÓN
    # ============================================================

    def start_session(self, width: int, height: int, fps: float | int) -> int:
        """
        Crea writers de vídeo (hasta 3 según configuración) y la fila de sesión en BD.
        
        Returns:
            session_id
        """
        self.frame_size = (width, height)
        self.fps = int(round(fps)) if fps else 30
        self.start_time = time.time()
        self.sequence_counter = 0  # Reset contador

        ts = timestamp()
        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        
        # ============================================================
        # CREAR VIDEOWRITERS SEGÚN CONFIGURACIÓN
        # ============================================================
        
        # 1. RAW (sin procesar)
        if self.generate_raw:
            self.video_path_raw = os.path.join(
                self.output_dir, f"{self.base_name}_raw_{width}x{height}_{self.fps}_{ts}.mp4"
            )
            self.video_writer_raw = cv2.VideoWriter(
                self.video_path_raw, fourcc, self.fps, self.frame_size
            )
            if not self.video_writer_raw or not self.video_writer_raw.isOpened():
                log.warning("VideoWriter RAW no está abierto tras start_session()")
            else:
                log.info("VideoWriter RAW creado: %s", self.video_path_raw)
        
        # 2. MEDIAPIPE (overlay completo MediaPipe)
        if self.generate_mediapipe:
            self.video_path_mediapipe = os.path.join(
                self.output_dir, f"{self.base_name}_mediapipe_{width}x{height}_{self.fps}_{ts}.mp4"
            )
            self.video_writer_mediapipe = cv2.VideoWriter(
                self.video_path_mediapipe, fourcc, self.fps, self.frame_size
            )
            if not self.video_writer_mediapipe or not self.video_writer_mediapipe.isOpened():
                log.warning("VideoWriter MEDIAPIPE no está abierto tras start_session()")
            else:
                log.info("VideoWriter MEDIAPIPE creado: %s", self.video_path_mediapipe)
        
        # 3. LEGACY (overlay clínico personalizado)
        if self.generate_legacy:
            self.video_path_legacy = os.path.join(
                self.output_dir, f"{self.base_name}_legacy_{width}x{height}_{self.fps}_{ts}.mp4"
            )
            self.video_writer_legacy = cv2.VideoWriter(
                self.video_path_legacy, fourcc, self.fps, self.frame_size
            )
            if not self.video_writer_legacy or not self.video_writer_legacy.isOpened():
                log.warning("VideoWriter LEGACY no está abierto tras start_session()")
            else:
                log.info("VideoWriter LEGACY creado: %s", self.video_path_legacy)

        # ============================================================
        # CREAR FILA EN BD
        # ============================================================
        log.info(
            "start_session: size=%s, fps=%s, patient=%s, exercise=%s",
            self.frame_size, self.fps, self.patient_id, self.exercise_id
        )
        
        self.session_id = crud.create_session(
            patient_id=self.patient_id,
            exercise_id=self.exercise_id,
            video_path_raw=self.video_path_raw,
            video_path_mediapipe=self.video_path_mediapipe,
            video_path_legacy=self.video_path_legacy,
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
        acumula métricas (ángulos y simetrías) para agregación final.
        
        Solo guarda si should_record_frame() == True
        """
        if self.session_id is None:
            log.error("record_frame_data llamado con session_id=None")
            raise RuntimeError("Session must be started before recording data.")

        # Verificar sampling rate
        if not self.should_record_frame():
            # Acumular métricas pero NO guardar en BD
            self._accumulate_metrics(joints)
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

        # Acumula métricas
        self._accumulate_metrics(joints)

    def _accumulate_metrics(self, joints: dict) -> None:
        """
        Acumula valores de ángulos y simetrías para cálculo de min/max/range al cerrar sesión.
        
        Detecta tanto "angle" como "symmetry" en los nombres de métricas.
        """
        for key, val in joints.items():
            # Filtrar métricas relevantes: ángulos articulares y simetrías
            if ("angle" in key or "symmetry" in key) and val is not None:
                try:
                    fval = float(val)
                    if not math.isnan(fval):
                        self.metric_records.setdefault(key, []).append(fval)
                except (TypeError, ValueError):
                    pass

    def write_video_frames(
        self, 
        frame_raw=None, 
        frame_mediapipe=None, 
        frame_legacy=None
    ) -> None:
        """
        Escribe frames a los vídeos de salida (según qué versiones estén activas).
        Incrementa el contador de secuencia.
        
        Args:
            frame_raw: Frame sin procesar (original)
            frame_mediapipe: Frame con overlay MediaPipe completo
            frame_legacy: Frame con overlay clínico personalizado
        """
        if self.video_writer_raw and frame_raw is not None:
            self.video_writer_raw.write(frame_raw)
        
        if self.video_writer_mediapipe and frame_mediapipe is not None:
            self.video_writer_mediapipe.write(frame_mediapipe)
        
        if self.video_writer_legacy and frame_legacy is not None:
            self.video_writer_legacy.write(frame_legacy)
        
        self._frames_written += 1
        self.sequence_counter += 1  # Incrementar contador de secuencia

    def get_sequence_counter(self) -> int:
        """
        Retorna el número de secuencia actual (frames escritos).
        
        Returns:
            Contador de secuencia (número del próximo frame a escribir)
        """
        return self.sequence_counter

    # ============================================================
    # CIERRE DE SESIÓN
    # ============================================================

    def close_session(self) -> None:
        """
        Libera recursos y calcula/guarda métricas agregadas (min/max/range).
        
        Diferencia unidades según tipo de métrica:
        - "degrees" para ángulos articulares y simetrías angulares
        - "pixels" para simetrías posicionales
        """
        log.info(
            "close_session ENTER sid=%s, frames_written=%s, frames_in_db=%s, sampling_rate=%s, sequence=%s",
            self.session_id, self._frames_written, self._frames_recorded_to_db, 
            self.sampling_rate, self.sequence_counter
        )

        # Cerrar los 3 writers
        if self.video_writer_raw:
            try:
                self.video_writer_raw.release()
                log.info("VideoWriter RAW cerrado")
            except Exception:
                log.exception("close_session: video_writer_raw.release() FAILED")
        
        if self.video_writer_mediapipe:
            try:
                self.video_writer_mediapipe.release()
                log.info("VideoWriter MEDIAPIPE cerrado")
            except Exception:
                log.exception("close_session: video_writer_mediapipe.release() FAILED")
        
        if self.video_writer_legacy:
            try:
                self.video_writer_legacy.release()
                log.info("VideoWriter LEGACY cerrado")
            except Exception:
                log.exception("close_session: video_writer_legacy.release() FAILED")

        if not self.session_id:
            log.warning("close_session: session_id is None (no se guardarán métricas).")
            return

        if not self.metric_records:
            log.info("close_session: sin registros de métricas para sid=%s", self.session_id)
            log.info(
                "close_session DONE: sid=%s, metrics_rows_saved=0, frames_written=%s",
                self.session_id, self._frames_written
            )
            return

        # Métricas clínicas agregadas
        saved = 0
        for metric_name, values in self.metric_records.items():
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

            # ============================================================
            # DETERMINAR UNIDAD SEGÚN TIPO DE MÉTRICA
            # ============================================================
            # Simetrías posicionales (verticales) usan "pixels"
            # Ángulos y simetrías angulares usan "degrees"
            if "symmetry" in metric_name and "_y" in metric_name:
                unit = "pixels"
            else:
                unit = "degrees"

            try:
                crud.add_metric(self.session_id, f"{metric_name}_max", mx, unit=unit)
                crud.add_metric(self.session_id, f"{metric_name}_min", mn, unit=unit)
                crud.add_metric(self.session_id, f"{metric_name}_range", rg, unit=unit)
                saved += 3
            except Exception:
                log.exception("FAILED saving metrics for '%s'", metric_name)

        log.info(
            "close_session DONE: sid=%s, metrics_rows=%s, frames_written=%s, frames_in_db=%s, "
            "videos=(raw=%s, mediapipe=%s, legacy=%s)",
            self.session_id, saved, self._frames_written, self._frames_recorded_to_db,
            self.video_path_raw, self.video_path_mediapipe, self.video_path_legacy
        )

    # ============================================================
    # UTILIDADES
    # ============================================================

    def elapsed_time(self) -> float:
        """Segundos transcurridos desde el inicio de la sesión."""
        if self.start_time:
            return round(time.time() - self.start_time, 2)
        return 0.0
    
    def get_video_paths(self) -> Tuple[str | None, str | None, str | None]:
        """
        Retorna las rutas de los 3 vídeos generados.
        
        Returns:
            Tupla (video_path_raw, video_path_mediapipe, video_path_legacy)
        """
        return (self.video_path_raw, self.video_path_mediapipe, self.video_path_legacy)