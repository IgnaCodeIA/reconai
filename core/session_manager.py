# core/session_manager.py
import os
import time
import math
import cv2
import subprocess
import numpy as np
from typing import Dict, List, Tuple

from core.utils import timestamp
from core.path_manager import get_exports_dir, check_disk_space
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
    - FFmpeg para máxima calidad de vídeo (bitrate alto)
    - FPS adaptativo para evitar aceleración
    """

    def __init__(
        self,
        output_dir: str | None = None,
        base_name: str = "session",
        patient_id: int | None = None,
        exercise_id: int | None = None,
        notes: str | None = None,
        sampling_rate: float = 0.0,
        # NUEVO: Flags para controlar qué versiones generar
        generate_raw: bool = False,
        generate_mediapipe: bool = False,
        generate_legacy: bool = True,
        # NUEVO: Control de calidad de video
        use_ffmpeg: bool = True,  # Usar FFmpeg para máxima calidad
        video_bitrate: str = "8000k",  # Bitrate muy alto para calidad profesional
    ):
        if output_dir is None:
            output_dir = str(get_exports_dir() / "videos")
        self.output_dir = output_dir
        
        # NUEVO: 3 VideoWriters (uno por cada versión) O FFmpeg pipes
        self.video_writer_raw: cv2.VideoWriter | None = None
        self.video_writer_mediapipe: cv2.VideoWriter | None = None
        self.video_writer_legacy: cv2.VideoWriter | None = None
        
        # FFmpeg processes (alternativa de alta calidad)
        self.ffmpeg_raw = None
        self.ffmpeg_mediapipe = None
        self.ffmpeg_legacy = None
        
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
        
        # NUEVO: Control de calidad
        self.use_ffmpeg = use_ffmpeg
        self.video_bitrate = video_bitrate

        log.info(
            "SessionManager created base_name=%s, patient=%s, exercise=%s, sampling_rate=%s, "
            "versions=(raw=%s, mediapipe=%s, legacy=%s), use_ffmpeg=%s, bitrate=%s",
            self.base_name, self.patient_id, self.exercise_id, self.sampling_rate,
            self.generate_raw, self.generate_mediapipe, self.generate_legacy,
            self.use_ffmpeg, self.video_bitrate
        )

    # ============================================================
    # INICIALIZACIÓN
    # ============================================================

    def _create_ffmpeg_writer(self, output_path: str, width: int, height: int, fps: int):
        """
        Crea un proceso FFmpeg para escribir video con máxima calidad.
        
        Args:
            output_path: Ruta del archivo de salida
            width: Ancho del video
            height: Alto del video
            fps: Frames por segundo
        
        Returns:
            Proceso de FFmpeg o None si falla
        """
        try:
            # Comando FFmpeg con máxima calidad
            cmd = [
                'ffmpeg',
                '-y',  # Sobrescribir archivo si existe
                '-f', 'rawvideo',
                '-vcodec', 'rawvideo',
                '-s', f'{width}x{height}',
                '-pix_fmt', 'bgr24',
                '-r', str(fps),
                '-i', '-',  # Entrada desde pipe
                '-an',  # Sin audio
                '-vcodec', 'libx264',  # Codec H.264
                '-preset', 'medium',  # Balance calidad/velocidad
                '-crf', '18',  # Calidad muy alta (0-51, menor=mejor, 18=visualmente sin pérdida)
                '-b:v', self.video_bitrate,  # Bitrate explícito
                '-pix_fmt', 'yuv420p',  # Compatibilidad
                '-movflags', '+faststart',  # Streaming optimizado
                output_path
            ]
            
            process = subprocess.Popen(
                cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE
            )
            
            log.info(f"FFmpeg writer creado: {output_path} ({width}x{height} @ {fps}fps, bitrate={self.video_bitrate}, CRF=18)")
            return process
            
        except FileNotFoundError:
            log.warning("FFmpeg no está instalado, usando OpenCV VideoWriter")
            return None
        except Exception as e:
            log.error(f"Error creando FFmpeg writer: {e}")
            return None

    def start_session(self, width: int, height: int, fps: float | int) -> int:
        """
        Crea writers de vídeo (hasta 3 según configuración) y la fila de sesión en BD.
        
        NUEVO: Usa FFmpeg con CRF=18 y bitrate alto para máxima calidad.
        
        Returns:
            session_id
        """
        self.frame_size = (width, height)
        self.fps = int(round(fps)) if fps else 20
        self.start_time = time.time()
        self.sequence_counter = 0  # Reset contador

        has_space, available_mb = check_disk_space(100)
        if not has_space:
            raise RuntimeError(f"Espacio insuficiente en disco. Disponible: {available_mb}MB")
        log.info(f"Espacio disponible en disco: {available_mb}MB")
        
        ts = timestamp()
        
        log.info(f"Iniciando sesión con resolución {width}x{height} @ {self.fps}fps")
        
        # ============================================================
        # CREAR WRITERS SEGÚN CONFIGURACIÓN (FFmpeg o OpenCV)
        # ============================================================
        
        if self.use_ffmpeg:
            log.info("Usando FFmpeg para máxima calidad (CRF=18, bitrate=%s)", self.video_bitrate)
            
            # 1. RAW (sin procesar) con FFmpeg
            if self.generate_raw:
                self.video_path_raw = os.path.join(
                    self.output_dir, f"{self.base_name}_raw_{width}x{height}_{self.fps}fps_{ts}.mp4"
                )
                self.ffmpeg_raw = self._create_ffmpeg_writer(self.video_path_raw, width, height, self.fps)
                if self.ffmpeg_raw:
                    log.info("FFmpeg RAW writer creado: %s", self.video_path_raw)
            
            # 2. MEDIAPIPE con FFmpeg
            if self.generate_mediapipe:
                self.video_path_mediapipe = os.path.join(
                    self.output_dir, f"{self.base_name}_mediapipe_{width}x{height}_{self.fps}fps_{ts}.mp4"
                )
                self.ffmpeg_mediapipe = self._create_ffmpeg_writer(self.video_path_mediapipe, width, height, self.fps)
                if self.ffmpeg_mediapipe:
                    log.info("FFmpeg MEDIAPIPE writer creado: %s", self.video_path_mediapipe)
            
            # 3. LEGACY con FFmpeg
            if self.generate_legacy:
                self.video_path_legacy = os.path.join(
                    self.output_dir, f"{self.base_name}_legacy_{width}x{height}_{self.fps}fps_{ts}.mp4"
                )
                self.ffmpeg_legacy = self._create_ffmpeg_writer(self.video_path_legacy, width, height, self.fps)
                if self.ffmpeg_legacy:
                    log.info("FFmpeg LEGACY writer creado: %s", self.video_path_legacy)
        
        else:
            # Fallback a OpenCV VideoWriter con mejor codec
            log.info("Usando OpenCV VideoWriter (calidad limitada)")
            
            # Intentar varios codecs en orden de preferencia
            fourcc_options = [
                ('H264', cv2.VideoWriter_fourcc(*'H264')),  # Mejor opción
                ('X264', cv2.VideoWriter_fourcc(*'X264')),  # Segunda opción
                ('avc1', cv2.VideoWriter_fourcc(*'avc1')),  # H.264 alternativo
                ('mp4v', cv2.VideoWriter_fourcc(*'mp4v')),  # Fallback básico
            ]
            
            fourcc = None
            for codec_name, codec_fourcc in fourcc_options:
                try:
                    # Test con writer temporal
                    test_writer = cv2.VideoWriter(
                        'test.mp4', codec_fourcc, self.fps, self.frame_size
                    )
                    if test_writer.isOpened():
                        fourcc = codec_fourcc
                        log.info(f"Usando codec: {codec_name}")
                        test_writer.release()
                        if os.path.exists('test.mp4'):
                            os.remove('test.mp4')
                        break
                except Exception:
                    continue
            
            if fourcc is None:
                fourcc = cv2.VideoWriter_fourcc(*'mp4v')
                log.warning("Usando codec mp4v (baja calidad)")
            
            # 1. RAW (sin procesar)
            if self.generate_raw:
                self.video_path_raw = os.path.join(
                    self.output_dir, f"{self.base_name}_raw_{width}x{height}_{self.fps}fps_{ts}.mp4"
                )
                self.video_writer_raw = cv2.VideoWriter(
                    self.video_path_raw, fourcc, self.fps, self.frame_size
                )
                if not self.video_writer_raw or not self.video_writer_raw.isOpened():
                    log.warning("VideoWriter RAW no está abierto")
                else:
                    log.info("OpenCV RAW writer creado: %s", self.video_path_raw)
            
            # 2. MEDIAPIPE
            if self.generate_mediapipe:
                self.video_path_mediapipe = os.path.join(
                    self.output_dir, f"{self.base_name}_mediapipe_{width}x{height}_{self.fps}fps_{ts}.mp4"
                )
                self.video_writer_mediapipe = cv2.VideoWriter(
                    self.video_path_mediapipe, fourcc, self.fps, self.frame_size
                )
                if not self.video_writer_mediapipe or not self.video_writer_mediapipe.isOpened():
                    log.warning("VideoWriter MEDIAPIPE no está abierto")
                else:
                    log.info("OpenCV MEDIAPIPE writer creado: %s", self.video_path_mediapipe)
            
            # 3. LEGACY
            if self.generate_legacy:
                self.video_path_legacy = os.path.join(
                    self.output_dir, f"{self.base_name}_legacy_{width}x{height}_{self.fps}fps_{ts}.mp4"
                )
                self.video_writer_legacy = cv2.VideoWriter(
                    self.video_path_legacy, fourcc, self.fps, self.frame_size
                )
                if not self.video_writer_legacy or not self.video_writer_legacy.isOpened():
                    log.warning("VideoWriter LEGACY no está abierto")
                else:
                    log.info("OpenCV LEGACY writer creado: %s", self.video_path_legacy)

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
        Escribe frames a los vídeos de salida (FFmpeg o OpenCV según configuración).
        Incrementa el contador de secuencia.
        
        Args:
            frame_raw: Frame sin procesar (original)
            frame_mediapipe: Frame con overlay MediaPipe completo
            frame_legacy: Frame con overlay clínico personalizado
        """
        # Escritura con FFmpeg (alta calidad)
        if self.use_ffmpeg:
            if self.ffmpeg_raw and frame_raw is not None:
                try:
                    self.ffmpeg_raw.stdin.write(frame_raw.tobytes())
                except Exception as e:
                    log.error(f"Error escribiendo frame RAW a FFmpeg: {e}")
            
            if self.ffmpeg_mediapipe and frame_mediapipe is not None:
                try:
                    self.ffmpeg_mediapipe.stdin.write(frame_mediapipe.tobytes())
                except Exception as e:
                    log.error(f"Error escribiendo frame MEDIAPIPE a FFmpeg: {e}")
            
            if self.ffmpeg_legacy and frame_legacy is not None:
                try:
                    self.ffmpeg_legacy.stdin.write(frame_legacy.tobytes())
                except Exception as e:
                    log.error(f"Error escribiendo frame LEGACY a FFmpeg: {e}")
        
        # Escritura con OpenCV VideoWriter
        else:
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

        # Cerrar FFmpeg processes
        if self.use_ffmpeg:
            if self.ffmpeg_raw:
                try:
                    self.ffmpeg_raw.stdin.close()
                    self.ffmpeg_raw.wait(timeout=10)
                    log.info("FFmpeg RAW cerrado")
                except Exception as e:
                    log.exception(f"Error cerrando FFmpeg RAW: {e}")
            
            if self.ffmpeg_mediapipe:
                try:
                    self.ffmpeg_mediapipe.stdin.close()
                    self.ffmpeg_mediapipe.wait(timeout=10)
                    log.info("FFmpeg MEDIAPIPE cerrado")
                except Exception as e:
                    log.exception(f"Error cerrando FFmpeg MEDIAPIPE: {e}")
            
            if self.ffmpeg_legacy:
                try:
                    self.ffmpeg_legacy.stdin.close()
                    self.ffmpeg_legacy.wait(timeout=10)
                    log.info("FFmpeg LEGACY cerrado")
                except Exception as e:
                    log.exception(f"Error cerrando FFmpeg LEGACY: {e}")
        
        # Cerrar OpenCV VideoWriters
        else:
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