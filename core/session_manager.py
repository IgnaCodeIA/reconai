import os
import sys
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

log = get_logger("core.session_manager")


class SessionManager:
    """Orchestrates a recording session: video writers, frame data, metrics, and DB persistence."""

    def __init__(
        self,
        output_dir: str | None = None,
        base_name: str = "session",
        patient_id: int | None = None,
        exercise_id: int | None = None,
        notes: str | None = None,
        sampling_rate: float = 0.0,
        generate_raw: bool = False,
        generate_mediapipe: bool = False,
        generate_legacy: bool = True,
        use_ffmpeg: bool = True,
        video_bitrate: str = "8000k",
    ):
        if output_dir is None:
            output_dir = str(get_exports_dir() / "videos")
        self.output_dir = output_dir
        os.makedirs(self.output_dir, exist_ok=True)
        log.info("Output directory: %s", self.output_dir)

        self.video_writer_raw: cv2.VideoWriter | None = None
        self.video_writer_mediapipe: cv2.VideoWriter | None = None
        self.video_writer_legacy: cv2.VideoWriter | None = None

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

        self.video_path_raw: str | None = None
        self.video_path_mediapipe: str | None = None
        self.video_path_legacy: str | None = None

        self.sampling_rate = sampling_rate
        self.last_sample_time = 0.0

        self.metric_records: Dict[str, List[float]] = {}

        self._frames_written = 0
        self._frames_recorded_to_db = 0

        self.sequence_counter = 0
        self.recording_active = False
        self._closing = False

        self.generate_raw = generate_raw
        self.generate_mediapipe = generate_mediapipe
        self.generate_legacy = generate_legacy

        self.use_ffmpeg = use_ffmpeg
        self.video_bitrate = video_bitrate

        log.info(
            "SessionManager created base_name=%s, patient=%s, exercise=%s, sampling_rate=%s, "
            "versions=(raw=%s, mediapipe=%s, legacy=%s), use_ffmpeg=%s, bitrate=%s",
            self.base_name, self.patient_id, self.exercise_id, self.sampling_rate,
            self.generate_raw, self.generate_mediapipe, self.generate_legacy,
            self.use_ffmpeg, self.video_bitrate
        )

    def _get_ffmpeg_path(self) -> str:
        """Resolve the ffmpeg executable path, checking PyInstaller bundle locations first then PATH."""
        if getattr(sys, 'frozen', False):
            candidates = [
                os.path.join(sys._MEIPASS, 'ffmpeg_bundle', 'ffmpeg.exe'),
                os.path.join(os.path.dirname(sys.executable), 'ffmpeg_bundle', 'ffmpeg.exe'),
                os.path.join(os.path.dirname(sys.executable), 'ffmpeg.exe'),
            ]
            for path in candidates:
                if os.path.exists(path):
                    log.info("FFmpeg found at: %s", path)
                    return path
            raise FileNotFoundError(
                f"ffmpeg.exe not found. Searched in: {candidates}"
            )
        else:
            dev_candidate = os.path.join(os.getcwd(), 'ffmpeg_bundle', 'ffmpeg.exe')
            if os.path.exists(dev_candidate):
                log.info("FFmpeg found at: %s", dev_candidate)
                return dev_candidate
            log.warning("FFmpeg not found locally, falling back to 'ffmpeg' on system PATH")
            return 'ffmpeg'

    def _create_ffmpeg_writer(self, output_path: str, width: int, height: int, fps: int):
        try:
            ffmpeg_bin = self._get_ffmpeg_path()
        except FileNotFoundError as e:
            log.error("FFmpeg not found, cannot create writer: %s", e)
            return None

        try:
            cmd = [
                ffmpeg_bin,
                '-y',
                '-f', 'rawvideo',
                '-vcodec', 'rawvideo',
                '-s', f'{width}x{height}',
                '-pix_fmt', 'bgr24',
                '-r', str(fps),
                '-i', '-',
                '-an',
                '-vcodec', 'libx264',
                '-preset', 'medium',
                '-crf', '18',
                '-b:v', self.video_bitrate,
                '-pix_fmt', 'yuv420p',
                '-movflags', '+faststart',
                output_path
            ]

            process = subprocess.Popen(
                cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                close_fds=False,
                creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == 'win32' else 0
            )

            log.info(
                "FFmpeg writer created: %s (%dx%d @ %dfps, bitrate=%s, CRF=18)",
                output_path, width, height, fps, self.video_bitrate
            )
            return process

        except FileNotFoundError:
            log.warning("FFmpeg is not installed, falling back to OpenCV VideoWriter")
            return None
        except Exception as e:
            log.error("Error creating FFmpeg writer: %s", e)
            return None

    def start_session(self, width: int, height: int, fps: float | int) -> int:
        """Initialize video writers and create the DB session row. Returns the new session_id."""
        log.debug(
            "start_session called with width=%s, height=%s, fps=%s",
            width, height, fps
        )
        self.frame_size = (width, height)
        self.fps = int(round(fps)) if fps else 20
        self.start_time = time.time()
        self.sequence_counter = 0

        has_space, available_mb = check_disk_space(100)
        if not has_space:
            raise RuntimeError(f"Insufficient disk space. Available: {available_mb}MB")
        log.info("Available disk space: %sMB", available_mb)

        ts = timestamp()

        log.info("Starting session at resolution %dx%d @ %dfps", width, height, self.fps)

        if self.use_ffmpeg:
            log.info("Using FFmpeg for maximum quality (CRF=18, bitrate=%s)", self.video_bitrate)

            if self.generate_raw:
                self.video_path_raw = os.path.join(
                    self.output_dir, f"{self.base_name}_raw_{width}x{height}_{self.fps}fps_{ts}.mp4"
                )
                self.ffmpeg_raw = self._create_ffmpeg_writer(self.video_path_raw, width, height, self.fps)
                if self.ffmpeg_raw:
                    log.info("FFmpeg RAW writer created: %s", self.video_path_raw)

            if self.generate_mediapipe:
                self.video_path_mediapipe = os.path.join(
                    self.output_dir, f"{self.base_name}_mediapipe_{width}x{height}_{self.fps}fps_{ts}.mp4"
                )
                self.ffmpeg_mediapipe = self._create_ffmpeg_writer(self.video_path_mediapipe, width, height, self.fps)
                if self.ffmpeg_mediapipe:
                    log.info("FFmpeg MEDIAPIPE writer created: %s", self.video_path_mediapipe)

            if self.generate_legacy:
                self.video_path_legacy = os.path.join(
                    self.output_dir, f"{self.base_name}_legacy_{width}x{height}_{self.fps}fps_{ts}.mp4"
                )
                self.ffmpeg_legacy = self._create_ffmpeg_writer(self.video_path_legacy, width, height, self.fps)
                if self.ffmpeg_legacy:
                    log.info("FFmpeg LEGACY writer created: %s", self.video_path_legacy)

        else:
            log.info("Using OpenCV VideoWriter (limited quality)")

            fourcc_options = [
                ('H264', cv2.VideoWriter_fourcc(*'H264')),
                ('X264', cv2.VideoWriter_fourcc(*'X264')),
                ('avc1', cv2.VideoWriter_fourcc(*'avc1')),
                ('mp4v', cv2.VideoWriter_fourcc(*'mp4v')),
            ]

            import tempfile
            fourcc = None
            for codec_name, codec_fourcc in fourcc_options:
                try:
                    with tempfile.NamedTemporaryFile(suffix='.mp4', delete=False) as tf:
                        test_path = tf.name
                    test_writer = cv2.VideoWriter(
                        test_path, codec_fourcc, self.fps, self.frame_size
                    )
                    if test_writer.isOpened():
                        fourcc = codec_fourcc
                        log.info("Using codec: %s", codec_name)
                        test_writer.release()
                    else:
                        test_writer.release()
                    try:
                        os.remove(test_path)
                    except Exception:
                        pass
                    if fourcc is not None:
                        break
                except Exception:
                    continue

            if fourcc is None:
                fourcc = cv2.VideoWriter_fourcc(*'mp4v')
                log.warning("Falling back to mp4v codec (low quality)")

            if self.generate_raw:
                self.video_path_raw = os.path.join(
                    self.output_dir, f"{self.base_name}_raw_{width}x{height}_{self.fps}fps_{ts}.mp4"
                )
                self.video_writer_raw = cv2.VideoWriter(
                    self.video_path_raw, fourcc, self.fps, self.frame_size
                )
                if not self.video_writer_raw or not self.video_writer_raw.isOpened():
                    log.warning("VideoWriter RAW is not open")
                else:
                    log.info("OpenCV RAW writer created: %s", self.video_path_raw)

            if self.generate_mediapipe:
                self.video_path_mediapipe = os.path.join(
                    self.output_dir, f"{self.base_name}_mediapipe_{width}x{height}_{self.fps}fps_{ts}.mp4"
                )
                self.video_writer_mediapipe = cv2.VideoWriter(
                    self.video_path_mediapipe, fourcc, self.fps, self.frame_size
                )
                if not self.video_writer_mediapipe or not self.video_writer_mediapipe.isOpened():
                    log.warning("VideoWriter MEDIAPIPE is not open")
                else:
                    log.info("OpenCV MEDIAPIPE writer created: %s", self.video_path_mediapipe)

            if self.generate_legacy:
                self.video_path_legacy = os.path.join(
                    self.output_dir, f"{self.base_name}_legacy_{width}x{height}_{self.fps}fps_{ts}.mp4"
                )
                self.video_writer_legacy = cv2.VideoWriter(
                    self.video_path_legacy, fourcc, self.fps, self.frame_size
                )
                if not self.video_writer_legacy or not self.video_writer_legacy.isOpened():
                    log.warning("VideoWriter LEGACY is not open")
                else:
                    log.info("OpenCV LEGACY writer created: %s", self.video_path_legacy)

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

    def should_record_frame(self) -> bool:
        """Return True if the current frame should be sampled for DB persistence."""
        if self.sampling_rate <= 0:
            return True

        elapsed = self.elapsed_time()
        if elapsed - self.last_sample_time >= self.sampling_rate:
            self.last_sample_time = elapsed
            return True
        return False

    def record_frame_data(self, frame_index: int, elapsed_time: float, joints: dict) -> None:
        """Persist per-frame joint data to the DB (subject to sampling) and accumulate metrics."""
        if self.session_id is None:
            log.error("record_frame_data called with session_id=None")
            raise RuntimeError("Session must be started before recording data.")

        if not self.should_record_frame():
            self._accumulate_metrics(joints)
            return

        data = {
            "time_seconds": elapsed_time,
            "frame": frame_index,
            **joints
        }

        try:
            crud.add_movement_data(self.session_id, data)
            self._frames_recorded_to_db += 1
        except Exception:
            log.exception("add_movement_data FAILED")

        self._accumulate_metrics(joints)

    def _accumulate_metrics(self, joints: dict) -> None:
        for key, val in joints.items():
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
        """Write the provided frames to their respective video outputs (raw / mediapipe / legacy)."""
        if self._closing:
            log.debug(
                "write_video_frames ignored: session is closing "
                "(frame discarded, this is normal)"
            )
            return

        if self.use_ffmpeg:
            if self.ffmpeg_raw and frame_raw is not None:
                try:
                    h, w = frame_raw.shape[:2]
                    self.ffmpeg_raw.stdin.write(np.ascontiguousarray(frame_raw[:h, :w]).tobytes())
                except Exception as e:
                    log.error("Error writing RAW frame to FFmpeg: %s", e)
                    rc = self.ffmpeg_raw.poll()
                    if rc is not None:
                        log.error("FFmpeg RAW process already dead (rc=%s)", rc)

            if self.ffmpeg_mediapipe and frame_mediapipe is not None:
                try:
                    h, w = frame_mediapipe.shape[:2]
                    self.ffmpeg_mediapipe.stdin.write(np.ascontiguousarray(frame_mediapipe[:h, :w]).tobytes())
                except Exception as e:
                    log.error("Error writing MEDIAPIPE frame to FFmpeg: %s", e)
                    rc = self.ffmpeg_mediapipe.poll()
                    if rc is not None:
                        log.error("FFmpeg MEDIAPIPE process already dead (rc=%s)", rc)

            if self.ffmpeg_legacy and frame_legacy is not None:
                try:
                    h, w = frame_legacy.shape[:2]
                    self.ffmpeg_legacy.stdin.write(np.ascontiguousarray(frame_legacy[:h, :w]).tobytes())
                except Exception as e:
                    log.error("Error writing LEGACY frame to FFmpeg: %s", e)
                    rc = self.ffmpeg_legacy.poll()
                    if rc is not None:
                        log.error("FFmpeg LEGACY process already dead (rc=%s)", rc)

        else:
            if self.video_writer_raw and frame_raw is not None:
                self.video_writer_raw.write(frame_raw)

            if self.video_writer_mediapipe and frame_mediapipe is not None:
                self.video_writer_mediapipe.write(frame_mediapipe)

            if self.video_writer_legacy and frame_legacy is not None:
                self.video_writer_legacy.write(frame_legacy)

        self._frames_written += 1
        self.sequence_counter += 1

    def get_sequence_counter(self) -> int:
        return self.sequence_counter

    def close_session(self) -> None:
        """Close all video writers, fix duration if needed, and aggregate metrics into the DB."""
        self._closing = True
        log.info(
            "close_session: _closing flag set — write_video_frames will block new FFmpeg writes"
        )
        real_duration = self.elapsed_time()
        log.info(
            "close_session ENTER sid=%s, frames_written=%s, frames_in_db=%s, sampling_rate=%s, sequence=%s, real_duration=%.2fs",
            self.session_id, self._frames_written, self._frames_recorded_to_db,
            self.sampling_rate, self.sequence_counter, real_duration
        )

        if self.use_ffmpeg:
            for proc, name in [
                (self.ffmpeg_raw, "RAW"),
                (self.ffmpeg_mediapipe, "MEDIAPIPE"),
                (self.ffmpeg_legacy, "LEGACY"),
            ]:
                if proc is None:
                    continue
                try:
                    if proc.stdin and not proc.stdin.closed:
                        proc.stdin.close()
                except Exception as e:
                    log.warning("Error closing FFmpeg %s stdin: %s", name, e)
            log.info("All FFmpeg stdin closed, waiting for completion...")

            for proc, name, video_path in [
                (self.ffmpeg_raw, "RAW", self.video_path_raw),
                (self.ffmpeg_mediapipe, "MEDIAPIPE", self.video_path_mediapipe),
                (self.ffmpeg_legacy, "LEGACY", self.video_path_legacy),
            ]:
                if proc is None:
                    continue
                try:
                    proc.wait(timeout=120)
                    rc = proc.returncode
                    if rc == 0:
                        file_size = os.path.getsize(video_path) / 1024 if video_path and os.path.exists(video_path) else 0
                        log.info("FFmpeg %s OK (rc=0) — file: %.1f KB → %s", name, file_size, video_path)
                    else:
                        log.error(
                            "FFmpeg %s exited with error rc=%s",
                            name, rc
                        )
                except subprocess.TimeoutExpired:
                    log.error(
                        "FFmpeg %s did not respond within 120s — returncode unknown, forcing kill",
                        name
                    )
                    proc.kill()
                    proc.wait()
                except Exception:
                    log.exception("Error waiting for FFmpeg %s", name)

        else:
            if self.video_writer_raw:
                try:
                    self.video_writer_raw.release()
                    log.info("VideoWriter RAW closed")
                except Exception:
                    log.exception("close_session: video_writer_raw.release() FAILED")

            if self.video_writer_mediapipe:
                try:
                    self.video_writer_mediapipe.release()
                    log.info("VideoWriter MEDIAPIPE closed")
                except Exception:
                    log.exception("close_session: video_writer_mediapipe.release() FAILED")

            if self.video_writer_legacy:
                try:
                    self.video_writer_legacy.release()
                    log.info("VideoWriter LEGACY closed")
                except Exception:
                    log.exception("close_session: video_writer_legacy.release() FAILED")

        if self._frames_written > 0 and real_duration > 0 and self.use_ffmpeg:
            for vpath in [self.video_path_raw, self.video_path_mediapipe, self.video_path_legacy]:
                self._fix_video_duration(vpath, real_duration)

        if not self.session_id:
            log.warning("close_session: session_id is None (metrics will not be saved).")
            return

        if not self.metric_records:
            log.info("close_session: no metric records for sid=%s", self.session_id)
            log.info(
                "close_session DONE: sid=%s, metrics_rows_saved=0, frames_written=%s",
                self.session_id, self._frames_written
            )
            return

        saved = 0
        for metric_name, values in self.metric_records.items():
            if not values:
                continue

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

    def elapsed_time(self) -> float:
        if self.start_time:
            return round(time.time() - self.start_time, 2)
        return 0.0

    def reset_start_time(self) -> None:
        """Reset the recording timer and activate recording. Call when actual recording begins."""
        self.start_time = time.time()
        self._frames_written = 0
        self.recording_active = True
        log.info("Recording timer reset and recording activated")

    def _fix_video_duration(self, video_path: str, real_duration: float) -> None:
        """Re-encode the video so its playback duration matches real_duration seconds."""
        if not video_path or not os.path.exists(video_path):
            return
        if self._frames_written <= 0 or real_duration <= 0 or not self.fps:
            return

        expected_duration = self._frames_written / self.fps
        if expected_duration <= 0:
            return

        ratio = real_duration / expected_duration
        if abs(ratio - 1.0) < 0.03:
            log.info(
                "Video duration within 3%% tolerance (expected=%.1fs, real=%.1fs), skipping fix for %s",
                expected_duration, real_duration, video_path
            )
            return

        log.info(
            "Fixing video duration: %.1fs → %.1fs (ratio=%.3f) for %s",
            expected_duration, real_duration, ratio, video_path
        )

        try:
            ffmpeg_bin = self._get_ffmpeg_path()
        except FileNotFoundError as e:
            log.warning("FFmpeg not available for duration fix: %s", e)
            return

        temp_path = video_path + ".duration_fix.mp4"
        try:
            cmd = [
                ffmpeg_bin, '-y',
                '-i', video_path,
                '-vf', f'setpts={ratio}*PTS',
                '-c:v', 'libx264',
                '-preset', 'fast',
                '-crf', '18',
                '-pix_fmt', 'yuv420p',
                '-movflags', '+faststart',
                '-an',
                temp_path
            ]
            result = subprocess.run(cmd, capture_output=True, timeout=300)
            if result.returncode == 0 and os.path.exists(temp_path):
                os.replace(temp_path, video_path)
                log.info("Video duration corrected: %s", video_path)
            else:
                err = result.stderr.decode('utf-8', errors='replace')[:300]
                log.warning("FFmpeg duration fix failed (rc=%s): %s", result.returncode, err)
        except Exception as e:
            log.error("Error fixing video duration for %s: %s", video_path, e)
        finally:
            if os.path.exists(temp_path):
                try:
                    os.remove(temp_path)
                except Exception:
                    pass

    def reinit_video_writers(self, width: int, height: int) -> None:
        """Reinitialize FFmpeg writers using the actual dimensions from the first frame."""
        if self.frame_size == (width, height):
            return

        log.info(
            "reinit_video_writers: actual dimensions %dx%d differ from %s, "
            "reinitializing FFmpeg writers",
            width, height, self.frame_size
        )

        for proc, _ in [
            (self.ffmpeg_raw, "RAW"),
            (self.ffmpeg_mediapipe, "MEDIAPIPE"),
            (self.ffmpeg_legacy, "LEGACY"),
        ]:
            if proc is None:
                continue
            try:
                if proc.stdin and not proc.stdin.closed:
                    proc.stdin.close()
                proc.wait(timeout=5)
            except Exception:
                try:
                    proc.kill()
                except Exception:
                    pass

        self.frame_size = (width, height)

        if self.generate_raw and self.video_path_raw:
            self.ffmpeg_raw = self._create_ffmpeg_writer(
                self.video_path_raw, width, height, self.fps
            )
            log.info("FFmpeg RAW reinitialized: %dx%d", width, height)

        if self.generate_mediapipe and self.video_path_mediapipe:
            self.ffmpeg_mediapipe = self._create_ffmpeg_writer(
                self.video_path_mediapipe, width, height, self.fps
            )
            log.info("FFmpeg MEDIAPIPE reinitialized: %dx%d", width, height)

        if self.generate_legacy and self.video_path_legacy:
            self.ffmpeg_legacy = self._create_ffmpeg_writer(
                self.video_path_legacy, width, height, self.fps
            )
            log.info("FFmpeg LEGACY reinitialized: %dx%d", width, height)

    def get_video_paths(self) -> Tuple[str | None, str | None, str | None]:
        return (self.video_path_raw, self.video_path_mediapipe, self.video_path_legacy)
