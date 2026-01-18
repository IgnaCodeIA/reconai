# ui/components/sessions.py
import os
import tempfile
import datetime
import time
import cv2
import numpy as np
import streamlit as st
from pathlib import Path

from db import crud
from core.session_manager import SessionManager
from core.pose_detection import PoseDetector
from core.video_capture import VideoCaptureManager
from core.legacy_overlay import draw_legacy_overlay
from core.utils import safe_round
from core.angle_calculator import calculate_angle
# ============================================================
# IMPORTS DE WEBRTC (CRÍTICO)
# ============================================================
try:
    from streamlit_webrtc import (
        VideoProcessorBase,
        webrtc_streamer,
        WebRtcMode,
        RTCConfiguration
    )
    _WEBRTC_OK = True
except ImportError:
    _WEBRTC_OK = False
    print("⚠️ streamlit-webrtc no está instalado")
# -------------------------------------------------------------
# WebRTC opcional (webcam en navegador). Si no está, se desactiva.
# -------------------------------------------------------------

# ============================================================
# CONFIGURACIÓN DE FPS
# ============================================================
# FPS realista para captura y procesamiento
# 20fps permite procesamiento estable sin pérdida de calidad
TARGET_FPS = 20

# -----------------------------
# UTILIDADES DE DIBUJO
# -----------------------------
def _draw_sequence_text(image_bgr, sequence: int) -> None:
    """
    Dibuja el contador de secuencia en la esquina superior izquierda (estilo Phiteca).
    
    Args:
        image_bgr: Frame BGR donde dibujar
        sequence: Número de secuencia actual
    """
    font = cv2.FONT_HERSHEY_SIMPLEX
    font_scale = 1
    thickness = 1
    
    # Rectángulo blanco de fondo (15, 5) a (250, 40)
    cv2.rectangle(image_bgr, (15, 5), (250, 40), (250, 250, 250), -1)
    
    # Texto en azul: "Secuencia: X"
    text = f'Secuencia: {sequence}'
    cv2.putText(image_bgr, text, (20, 30), font, font_scale, (255, 0, 0), thickness, cv2.LINE_AA)


# -----------------------------
# Estado local de la página
# -----------------------------
def _init_state():
    st.session_state.setdefault("record_mode", False)
    st.session_state.setdefault("paused", False)
    st.session_state.setdefault("save_prompt", False)
    st.session_state.setdefault("source_mode", "Webcam (WebRTC)")
    st.session_state.setdefault("selected_patient", None)
    st.session_state.setdefault("selected_exercise", None)
    st.session_state.setdefault("notes", "")
    st.session_state.setdefault("delete_candidate", None)
    st.session_state.setdefault("sampling_rate", 0.0)
    # NUEVO: Flags de versiones de vídeo
    st.session_state.setdefault("generate_raw", False)
    st.session_state.setdefault("generate_mediapipe", False)
    st.session_state.setdefault("generate_legacy", True)


def _overlay_rec(image_bgr, paused=False, landmarks_found=False):
    """Dibuja indicador REC/PAUSA en el frame."""
    color = (0, 0, 255) if not paused else (0, 165, 255)
    cv2.circle(image_bgr, (30, 30), 10, color, -1)
    label = "REC" if not paused else "PAUSA"
    cv2.putText(image_bgr, label, (50, 36), cv2.FONT_HERSHEY_SIMPLEX, 0.8, color, 2)
    txt = "LMK: OK" if landmarks_found else "LMK: --"
    cv2.putText(image_bgr, txt, (30, 66), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (200, 200, 200), 2)
    return image_bgr


def _reset_record_ui_state():
    """Resetea estados de grabación."""
    st.session_state["record_mode"] = False
    st.session_state["paused"] = False
    st.session_state["save_prompt"] = False


def _safe_resolve_id(selected_name, options_dict):
    """Evita KeyError si el nombre cambió. Devuelve un id válido."""
    if not options_dict:
        return None
    if selected_name in options_dict:
        return options_dict[selected_name]
    return next(iter(options_dict.values()))


def _extract_joint_data(lm, w, h):
    """
    Extrae TODOS los datos biomecánicos necesarios (brazos, piernas, pies)
    y calcula métricas de simetría bilateral.
    
    Returns:
        tuple: (joint_data dict, angles dict) o (None, {}) si faltan landmarks
    """
    try:
        # Extracción de coordenadas (normalizadas → píxeles)
        shoulder_r = (lm["RIGHT_SHOULDER"][0] * w, lm["RIGHT_SHOULDER"][1] * h)
        elbow_r = (lm["RIGHT_ELBOW"][0] * w, lm["RIGHT_ELBOW"][1] * h)
        wrist_r = (lm["RIGHT_WRIST"][0] * w, lm["RIGHT_WRIST"][1] * h)
        
        shoulder_l = (lm["LEFT_SHOULDER"][0] * w, lm["LEFT_SHOULDER"][1] * h)
        elbow_l = (lm["LEFT_ELBOW"][0] * w, lm["LEFT_ELBOW"][1] * h)
        wrist_l = (lm["LEFT_WRIST"][0] * w, lm["LEFT_WRIST"][1] * h)
        
        hip_r = (lm["RIGHT_HIP"][0] * w, lm["RIGHT_HIP"][1] * h)
        knee_r = (lm["RIGHT_KNEE"][0] * w, lm["RIGHT_KNEE"][1] * h)
        ankle_r = (lm["RIGHT_ANKLE"][0] * w, lm["RIGHT_ANKLE"][1] * h)
        
        hip_l = (lm["LEFT_HIP"][0] * w, lm["LEFT_HIP"][1] * h)
        knee_l = (lm["LEFT_KNEE"][0] * w, lm["LEFT_KNEE"][1] * h)
        ankle_l = (lm["LEFT_ANKLE"][0] * w, lm["LEFT_ANKLE"][1] * h)
        
        heel_r = (lm["RIGHT_HEEL"][0] * w, lm["RIGHT_HEEL"][1] * h)
        foot_index_r = (lm["RIGHT_FOOT_INDEX"][0] * w, lm["RIGHT_FOOT_INDEX"][1] * h)
        heel_l = (lm["LEFT_HEEL"][0] * w, lm["LEFT_HEEL"][1] * h)
        foot_index_l = (lm["LEFT_FOOT_INDEX"][0] * w, lm["LEFT_FOOT_INDEX"][1] * h)
        
        # Cálculo de ángulos articulares
        angle_arm_r = calculate_angle(shoulder_r, elbow_r, wrist_r)
        angle_arm_l = calculate_angle(shoulder_l, elbow_l, wrist_l)
        angle_leg_r = calculate_angle(hip_r, knee_r, ankle_r)
        angle_leg_l = calculate_angle(hip_l, knee_l, ankle_l)
        
        angles = {
            "angle_arm_r": angle_arm_r,
            "angle_arm_l": angle_arm_l,
            "angle_leg_r": angle_leg_r,
            "angle_leg_l": angle_leg_l,
        }
        
        # Cálculo de simetrías
        symmetry_angle_arm = None
        if angle_arm_r is not None and angle_arm_l is not None:
            symmetry_angle_arm = abs(angle_arm_r - angle_arm_l)
        
        symmetry_angle_leg = None
        if angle_leg_r is not None and angle_leg_l is not None:
            symmetry_angle_leg = abs(angle_leg_r - angle_leg_l)
        
        symmetry_shoulder_y = abs(shoulder_r[1] - shoulder_l[1])
        symmetry_elbow_y = abs(elbow_r[1] - elbow_l[1])
        symmetry_knee_y = abs(knee_r[1] - knee_l[1])
        
        # Construcción del diccionario completo
        joint_data = {
            # Brazos
            "shoulder_x_r": shoulder_r[0], "shoulder_y_r": shoulder_r[1],
            "elbow_x_r": elbow_r[0], "elbow_y_r": elbow_r[1],
            "wrist_x_r": wrist_r[0], "wrist_y_r": wrist_r[1],
            "angle_arm_r": angle_arm_r,
            
            "shoulder_x_l": shoulder_l[0], "shoulder_y_l": shoulder_l[1],
            "elbow_x_l": elbow_l[0], "elbow_y_l": elbow_l[1],
            "wrist_x_l": wrist_l[0], "wrist_y_l": wrist_l[1],
            "angle_arm_l": angle_arm_l,
            
            # Piernas
            "hip_x_r": hip_r[0], "hip_y_r": hip_r[1],
            "knee_x_r": knee_r[0], "knee_y_r": knee_r[1],
            "ankle_x_r": ankle_r[0], "ankle_y_r": ankle_r[1],
            "angle_leg_r": angle_leg_r,
            
            "hip_x_l": hip_l[0], "hip_y_l": hip_l[1],
            "knee_x_l": knee_l[0], "knee_y_l": knee_l[1],
            "ankle_x_l": ankle_l[0], "ankle_y_l": ankle_l[1],
            "angle_leg_l": angle_leg_l,
            
            # Pies
            "heel_x_r": heel_r[0], "heel_y_r": heel_r[1],
            "foot_index_x_r": foot_index_r[0], "foot_index_y_r": foot_index_r[1],
            "heel_x_l": heel_l[0], "heel_y_l": heel_l[1],
            "foot_index_x_l": foot_index_l[0], "foot_index_y_l": foot_index_l[1],
            
            # Simetrías
            "symmetry_angle_arm": symmetry_angle_arm,
            "symmetry_angle_leg": symmetry_angle_leg,
            "symmetry_shoulder_y": symmetry_shoulder_y,
            "symmetry_elbow_y": symmetry_elbow_y,
            "symmetry_knee_y": symmetry_knee_y,
        }
        
        return joint_data, angles
        
    except KeyError as e:
        print(f"⚠️ Landmarks incompletos, falta: {e}")
        return None, {}


# ============================================================
# Procesador WebRTC
# ============================================================
class Processor(VideoProcessorBase):
    """
    Procesador de vídeo para streamlit-webrtc con soporte para 3 versiones de salida,
    contador de secuencia visible y FPS controlado para evitar aceleración.
    """
    
    def __init__(self, patient_id, exercise_id, notes, sampling_rate=0.0,
                 generate_raw=False, generate_mediapipe=False, generate_legacy=True):
        self.patient_id = patient_id
        self.exercise_id = exercise_id
        self.notes = notes
        self.sampling_rate = sampling_rate
        self.generate_raw = generate_raw
        self.generate_mediapipe = generate_mediapipe
        self.generate_legacy = generate_legacy

        self.detector = PoseDetector()
        self.session_mgr: SessionManager | None = None
        self.frame_idx = 0
        self.started = False

    def _ensure_session(self, w: int, h: int, fps_hint: int = TARGET_FPS):
        """Inicializa la sesión en el primer frame con FPS realista."""
        if not self.started:
            self.session_mgr = SessionManager(
                output_dir="data/exports",
                base_name="captura_webcam",
                patient_id=self.patient_id,
                exercise_id=self.exercise_id,
                notes=self.notes,
                sampling_rate=self.sampling_rate,
                generate_raw=self.generate_raw,
                generate_mediapipe=self.generate_mediapipe,
                generate_legacy=self.generate_legacy,
            )
            self.sid = self.session_mgr.start_session(w, h, fps_hint)
            self.started = True
            print(f"✅ Sesión iniciada: ID={self.sid} @ {fps_hint}fps")

    def recv(self, frame: "av.VideoFrame") -> "av.VideoFrame":
        """Procesa cada frame del stream de vídeo y genera las 3 versiones."""
        img_bgr = frame.to_ndarray(format="bgr24")
        h, w = img_bgr.shape[:2]

        # Sesión al primer frame con FPS realista
        self._ensure_session(w, h, fps_hint=TARGET_FPS)

        # Obtener número de secuencia ANTES de escribir
        sequence_num = self.session_mgr.get_sequence_counter()

        # ============================================================
        # GENERACIÓN DE LAS 3 VERSIONES DE FRAME
        # ============================================================
        
        # 1. Frame RAW (sin procesar) - copia del original CON secuencia
        frame_raw = None
        if self.generate_raw:
            frame_raw = img_bgr.copy()
            _draw_sequence_text(frame_raw, sequence_num)
        
        # 2. Procesamiento de pose
        image_bgr, results = self.detector.process_frame(img_bgr)
        landmarks_found = bool(results and results.pose_landmarks)

        # ============================================================
        # 3. Frame MEDIAPIPE (⚪ FONDO BLANCO + esqueleto) CON secuencia
        # ============================================================
        frame_mediapipe = None
        if self.generate_mediapipe:
            if landmarks_found:
                # NUEVO: Dibujar sobre fondo blanco en lugar del video original
                frame_mediapipe = self.detector.draw_mediapipe_on_white_background(
                    w, h, results, sequence=sequence_num
                )
            else:
                # Si no hay landmarks, frame blanco con contador
                frame_mediapipe = np.ones((h, w, 3), dtype=np.uint8) * 255
                _draw_sequence_text(frame_mediapipe, sequence_num)
        
        # 4. Frame LEGACY (overlay clínico personalizado) CON secuencia
        frame_legacy = None
        if self.generate_legacy:
            frame_legacy = image_bgr.copy()
            if landmarks_found:
                lm = self.detector.extract_landmarks(results)
                joint_data, angles = _extract_joint_data(lm, w, h)
                
                if joint_data:
                    frame_legacy = draw_legacy_overlay(
                        frame_legacy, lm, w, h,
                        angles=angles,
                        a_max=60.0,
                        sequence=sequence_num  # NUEVO: Pasar contador
                    )

                    # Registro en BD (solo si no está en pausa)
                    if self.session_mgr and not st.session_state.get("paused", False):
                        try:
                            self.session_mgr.record_frame_data(
                                frame_index=self.frame_idx,
                                elapsed_time=self.session_mgr.elapsed_time(),
                                joints=joint_data
                            )
                        except Exception as e:
                            print(f"❌ Error al registrar frame {self.frame_idx}: {e}")
                else:
                    # Si no hay landmarks, al menos dibujar la secuencia
                    _draw_sequence_text(frame_legacy, sequence_num)
            else:
                # Si no hay landmarks, al menos dibujar la secuencia
                _draw_sequence_text(frame_legacy, sequence_num)

        # ============================================================
        # ESCRITURA DE VÍDEOS (solo si no está en pausa)
        # ============================================================
        if self.session_mgr and not st.session_state.get("paused", False):
            self.session_mgr.write_video_frames(
                frame_raw=frame_raw,
                frame_mediapipe=frame_mediapipe,
                frame_legacy=frame_legacy
            )
            self.frame_idx += 1

        # ============================================================
        # FRAME DE RETORNO (mostrar al usuario)
        # ============================================================
        # Prioridad: legacy > mediapipe > raw
        display_frame = frame_legacy if frame_legacy is not None else \
                       frame_mediapipe if frame_mediapipe is not None else \
                       frame_raw if frame_raw is not None else image_bgr
        
        # Overlay REC/PAUSA
        display_frame = _overlay_rec(display_frame, 
                                     paused=st.session_state.get("paused", False), 
                                     landmarks_found=landmarks_found)
        
        return av.VideoFrame.from_ndarray(display_frame, format="bgr24")

    def close_and_save(self):
        """Cierra y guarda la sesión."""
        if self.session_mgr:
            print(f"💾 Cerrando sesión ID={self.session_mgr.session_id}...")
            self.session_mgr.close_session()
            return self.session_mgr.session_id, self.session_mgr.get_video_paths()
        return None, (None, None, None)

    def close_and_discard(self):
        """Cierra y descarta la sesión."""
        sid, paths = None, (None, None, None)
        if self.session_mgr:
            sid = self.session_mgr.session_id
            paths = self.session_mgr.get_video_paths()
            try:
                self.session_mgr.close_session()
            except Exception:
                pass
            if sid:
                try:
                    crud.delete_session(sid)
                    print(f"🗑️ Sesión {sid} descartada")
                except Exception:
                    pass
            # Eliminar archivos de vídeo
            for path in paths:
                if path and os.path.exists(path):
                    try:
                        os.remove(path)
                    except Exception:
                        pass
        return sid, paths

    def release_models(self):
        """Libera recursos de MediaPipe."""
        try:
            self.detector.release()
        except Exception:
            pass


# ============================================================
# APP PRINCIPAL
# ============================================================
def app():
    _init_state()

    st.title("Gestión de Sesiones")
    st.write("Cree nuevas sesiones de análisis, revise grabaciones y consulte métricas registradas.")

    # Cargar datos base
    try:
        patients = crud.get_all_patients()
        exercises = crud.get_all_exercises()
    except Exception as e:
        st.error(f"Error al cargar datos: {e}")
        return

    if not patients:
        st.warning("No hay pacientes registrados. Agregue uno primero en la sección Pacientes.")
        return
    if not exercises:
        st.warning("No hay ejercicios definidos. Cree uno primero en la sección Ejercicios.")
        return

    patient_options = {p[1]: p[0] for p in patients}
    exercise_options = {e[1]: e[0] for e in exercises}

    st.subheader("Registrar nueva sesión")

    # ============================================================
    # FORMULARIO DE INICIO CON OPCIONES DE VÍDEO
    # ============================================================
    with st.form("session_form", clear_on_submit=False):
        col_sel = st.columns(3)
        with col_sel[0]:
            selected_patient = st.selectbox("Paciente", list(patient_options.keys()))
        with col_sel[1]:
            selected_exercise = st.selectbox("Ejercicio", list(exercise_options.keys()))
        with col_sel[2]:
            source_mode = st.selectbox(
                "Fuente",
                ["Webcam (WebRTC)", "Subir vídeo"],
                index=0 if _WEBRTC_OK else 1
            )

        notes = st.text_area("Observaciones clínicas (opcional)")
        
        # NUEVO: Selector de versiones de vídeo
        st.write("**Versiones de vídeo a generar:**")
        col_vid = st.columns(3)
        with col_vid[0]:
            generate_raw = st.checkbox(
                "🎬 Sin procesar (RAW)", 
                value=False,
                help="Vídeo original sin overlays"
            )
        with col_vid[1]:
            generate_mediapipe = st.checkbox(
                "🤖 MediaPipe completo", 
                value=False,
                help="⚪ Fondo blanco + esqueleto de pose (33 puntos)"
            )
        with col_vid[2]:
            generate_legacy = st.checkbox(
                "⚕️ Overlay clínico", 
                value=True,
                help="Barritas, puntos y ángulos (recomendado)"
            )
        
        # Botón rápido para generar las 3
        if st.checkbox("✅ Generar todas las versiones", value=False):
            generate_raw = generate_mediapipe = generate_legacy = True
        
        # Opción de sampling rate
        with st.expander("⚙️ Configuración avanzada"):
            use_sampling = st.checkbox("Reducir frecuencia de muestreo", 
                                      help="Guarda menos frames en BD para ahorrar espacio")
            if use_sampling:
                sampling_rate = st.slider("Segundos entre muestras", 0.1, 1.0, 0.2, 0.05)
            else:
                sampling_rate = 0.0
            
            st.info(f"ℹ️ Los videos se grabarán a {TARGET_FPS} fps para óptima calidad y velocidad correcta")

        if source_mode == "Webcam (WebRTC)" and not _WEBRTC_OK:
            st.info("Para usar la webcam en el navegador: `pip install streamlit-webrtc av`")

        start_btn = st.form_submit_button("Iniciar sesión")

        if start_btn:
            # Validación: al menos una versión debe estar seleccionada
            if not (generate_raw or generate_mediapipe or generate_legacy):
                st.error("⚠️ Debe seleccionar al menos una versión de vídeo")
            else:
                st.session_state["selected_patient"] = selected_patient
                st.session_state["selected_exercise"] = selected_exercise
                st.session_state["notes"] = notes
                st.session_state["source_mode"] = source_mode
                st.session_state["sampling_rate"] = sampling_rate
                st.session_state["generate_raw"] = generate_raw
                st.session_state["generate_mediapipe"] = generate_mediapipe
                st.session_state["generate_legacy"] = generate_legacy
                st.session_state["record_mode"] = True
                st.session_state["paused"] = False
                st.session_state["save_prompt"] = False
                st.rerun()

    # ============================================================
    # MODO 1: Webcam (WebRTC)
    # ============================================================
    if st.session_state.get("record_mode") and st.session_state.get("source_mode") == "Webcam (WebRTC)":
        if not _WEBRTC_OK:
            st.error("streamlit-webrtc no está instalado.")
            return

        st.subheader("📹 Grabación con webcam (en vivo)")
        
        # Mostrar versiones activas
        versions = []
        if st.session_state.get("generate_raw"): versions.append("RAW")
        if st.session_state.get("generate_mediapipe"): versions.append("⚪ MediaPipe (fondo blanco)")
        if st.session_state.get("generate_legacy"): versions.append("Clínico")
        st.info(f"🎬 Generando versiones: {', '.join(versions)} @ {TARGET_FPS}fps")
        
        # ============================================================
        # OCULTAR BOTONES NATIVOS DE STREAMLIT-WEBRTC CON CSS
        # ============================================================
        st.markdown("""
        <style>
        /* Ocultar botones nativos de streamlit-webrtc */
        button[kind="header"] {
            display: none !important;
        }
        div[data-testid="stToolbar"] {
            display: none !important;
        }
        /* Ocultar el botón Start y Select device */
        .streamlit-webrtc-controls {
            display: none !important;
        }
        /* Ocultar controles de video nativos */
        div.css-1n76uvr, div.css-12oz5g7 {
            display: none !important;
        }
        </style>
        """, unsafe_allow_html=True)
        
        # ============================================================
        # CONTROLES PERSONALIZADOS (GRANDES Y CLAROS)
        # ============================================================
        st.markdown("### Controles de grabación")
        
        ctrl_cols = st.columns([2, 2, 1])
        
        with ctrl_cols[0]:
            if st.session_state.get("paused", False):
                if st.button("▶️ Reanudar grabación", type="primary", use_container_width=True):
                    st.session_state["paused"] = False
                    st.rerun()
            else:
                if st.button("⏸️ Pausar grabación", use_container_width=True):
                    st.session_state["paused"] = True
                    st.rerun()
        
        with ctrl_cols[1]:
            if st.button("⏹️ Finalizar y guardar", type="secondary", use_container_width=True):
                st.session_state["save_prompt"] = True
                st.session_state["paused"] = True
                st.rerun()
        
        with ctrl_cols[2]:
            # Indicador de estado
            if st.session_state.get("paused", False):
                st.warning("⏸️ PAUSADO")
            else:
                st.success("🔴 GRABANDO")
        
        st.markdown("---")

        try:
            rtc_configuration = RTCConfiguration(
                {"iceServers": [{"urls": ["stun:stun.l.google.com:19302"]}]}
            )
        except Exception:
            rtc_configuration = {"iceServers": [{"urls": ["stun:stun.l.google.com:19302"]}]}

        pid = _safe_resolve_id(st.session_state["selected_patient"], patient_options)
        eid = _safe_resolve_id(st.session_state["selected_exercise"], exercise_options)
        nts = st.session_state["notes"]
        sr = st.session_state.get("sampling_rate", 0.0)
        gen_raw = st.session_state.get("generate_raw", False)
        gen_mp = st.session_state.get("generate_mediapipe", False)
        gen_leg = st.session_state.get("generate_legacy", True)

        # ============================================================
        # CONSTRAINTS DE VIDEO CON FPS LIMITADO (CRÍTICO PARA EVITAR ACELERACIÓN)
        # ============================================================
        media_stream_constraints = {
            "video": {
                "frameRate": {"ideal": TARGET_FPS, "max": TARGET_FPS}  # Limitar FPS de captura
            },
            "audio": False
        }

        # Estado inicial: siempre playing (auto-start)
        ctx = webrtc_streamer(
            key="recon-ia-webrtc",
            mode=WebRtcMode.SENDRECV,
            rtc_configuration=rtc_configuration,
            media_stream_constraints=media_stream_constraints,  # FPS limitado
            video_processor_factory=lambda: Processor(
                pid, eid, nts, sr, gen_raw, gen_mp, gen_leg
            ),
            async_processing=True,
            desired_playing_state=True,  # Auto-iniciar
        )

        # ============================================================
        # DIÁLOGO DE CONFIRMACIÓN (MEJORADO)
        # ============================================================
        if st.session_state.get("save_prompt"):
            st.markdown("---")
            st.markdown("### 💾 Finalizar sesión")
            
            # Información de la sesión
            st.info(f"""
            **Sesión actual:**
            - Paciente: {st.session_state.get('selected_patient', 'N/A')}
            - Ejercicio: {st.session_state.get('selected_exercise', 'N/A')}
            - Versiones generadas: {', '.join(versions)}
            """)
            
            st.warning("⚠️ ¿Desea guardar esta sesión?")
            
            bcols = st.columns([2, 2, 1])
            
            with bcols[0]:
                if st.button("✅ Guardar sesión", type="primary", use_container_width=True):
                    with st.spinner("Guardando sesión..."):
                        if ctx and ctx.video_processor:
                            sid, paths = ctx.video_processor.close_and_save()
                            ctx.video_processor.release_models()
                            try:
                                ctx.stop()
                            except Exception:
                                pass
                            if sid:
                                st.success(f"✅ Sesión guardada correctamente (ID {sid})")
                                raw_path, mp_path, leg_path = paths
                                if raw_path: 
                                    st.caption(f"📹 RAW: {os.path.basename(raw_path)}")
                                if mp_path: 
                                    st.caption(f"⚪ MediaPipe: {os.path.basename(mp_path)}")
                                if leg_path: 
                                    st.caption(f"⚕️ Clínico: {os.path.basename(leg_path)}")
                                time.sleep(1.5)  # Dar tiempo para leer el mensaje
                        _reset_record_ui_state()
                        st.rerun()

            with bcols[1]:
                if st.button("🗑️ Descartar sesión", use_container_width=True):
                    with st.spinner("Descartando sesión..."):
                        if ctx and ctx.video_processor:
                            sid, paths = ctx.video_processor.close_and_discard()
                            ctx.video_processor.release_models()
                            try:
                                ctx.stop()
                            except Exception:
                                pass
                        st.info("Sesión descartada correctamente")
                        time.sleep(1)
                    _reset_record_ui_state()
                    st.rerun()

            with bcols[2]:
                if st.button("↩️ Volver", use_container_width=True):
                    st.session_state["save_prompt"] = False
                    st.session_state["paused"] = False
                    st.rerun()

    # ============================================================
    # MODO 2: Subir vídeo (análisis batch)
    # ============================================================
    if st.session_state.get("record_mode") and st.session_state.get("source_mode") == "Subir vídeo":
        from core.file_validator import FileValidator
        from core.path_manager import get_temp_dir
        import uuid
        
        st.subheader("Análisis desde archivo de vídeo")
        
        # Mostrar versiones activas
        versions = []
        if st.session_state.get("generate_raw"): versions.append("RAW")
        if st.session_state.get("generate_mediapipe"): versions.append("MediaPipe (fondo blanco)")
        if st.session_state.get("generate_legacy"): versions.append("Clínico")
        st.info(f"Versiones a generar: {', '.join(versions)}")
        
        uploaded = st.file_uploader(
            "Seleccione un archivo de video", 
            type=["mp4", "mov", "avi", "mpeg", "mpg", "m4v", "mkv"],
            help=f"Formatos soportados: MP4, MOV, AVI. Máximo {FileValidator.MAX_VIDEO_SIZE_MB}MB"
        )

        if uploaded is None:
            st.info("Suba un video para analizar y guardar la sesión.")
        else:
            # Mostrar información del archivo subido
            file_size_mb = uploaded.size / (1024 * 1024)
            st.write(f"**Archivo:** {uploaded.name}")
            st.write(f"**Tamaño:** {file_size_mb:.2f} MB")
            
            # Verificar tamaño antes de procesar
            if file_size_mb > FileValidator.MAX_VIDEO_SIZE_MB:
                st.error(f"El archivo es demasiado grande ({file_size_mb:.1f}MB). Máximo permitido: {FileValidator.MAX_VIDEO_SIZE_MB}MB")
                if st.button("Cancelar"):
                    _reset_record_ui_state()
                    st.rerun()
            else:
                # Estado para almacenar resultado de validación
                if 'validation_result' not in st.session_state:
                    st.session_state.validation_result = None
                
                # Botón de validación
                if st.session_state.validation_result is None:
                    if st.button("Validar archivo", type="primary"):
                        with st.spinner("Validando archivo..."):
                            # Guardar temporalmente para validar
                            temp_dir = get_temp_dir()
                            temp_filename = f"validate_{uuid.uuid4().hex[:8]}_{uploaded.name}"
                            temp_path = temp_dir / temp_filename
                            
                            try:
                                with open(temp_path, "wb") as f:
                                    f.write(uploaded.getvalue())
                                
                                # Validar
                                is_valid, message, metadata = FileValidator.validate_video(temp_path)
                                
                                st.session_state.validation_result = {
                                    'valid': is_valid,
                                    'message': message,
                                    'metadata': metadata,
                                    'temp_path': str(temp_path)
                                }
                                
                            except Exception as e:
                                st.session_state.validation_result = {
                                    'valid': False,
                                    'message': f"Error al validar: {str(e)}",
                                    'metadata': {},
                                    'temp_path': str(temp_path)
                                }
                            
                            st.rerun()
                
                # Mostrar resultado de validación
                if st.session_state.validation_result is not None:
                    result = st.session_state.validation_result
                    
                    if result['valid']:
                        st.success(f"Video válido: {result['message']}")
                        
                        # Mostrar metadata
                        meta = result['metadata']
                        col1, col2, col3 = st.columns(3)
                        with col1:
                            st.metric("Resolución", f"{meta.get('width', 0)}x{meta.get('height', 0)}")
                        with col2:
                            st.metric("FPS", f"{meta.get('fps', 0):.1f}")
                        with col3:
                            st.metric("Duración", f"{meta.get('duration_sec', 0)}s")
                        
                        st.caption(f"Frames: {meta.get('frame_count', 0)} | Codec: {meta.get('codec', 'unknown')}")
                        
                        # Verificar espacio en disco
                        from core.path_manager import check_disk_space
                        estimated_size_mb = file_size_mb * 3  # Estimación: original + 3 versiones procesadas
                        has_space, available_mb = check_disk_space(int(estimated_size_mb))
                        
                        if not has_space:
                            st.error(f"Espacio insuficiente en disco. Necesario: ~{estimated_size_mb:.0f}MB, Disponible: {available_mb}MB")
                        else:
                            st.info(f"Espacio disponible: {available_mb}MB (necesario: ~{estimated_size_mb:.0f}MB)")
                            
                            # Botón para analizar
                            col_analyze, col_cancel = st.columns(2)
                            
                            with col_analyze:
                                if st.button("Analizar video", type="primary", use_container_width=True):
                                    temp_path = result['temp_path']
                                    
                                    try:
                                        cap = VideoCaptureManager(temp_path)
                                    except Exception as e:
                                        st.error(f"No se pudo abrir el video: {e}")
                                        st.session_state.validation_result = None
                                        st.stop()

                                    pid = _safe_resolve_id(st.session_state["selected_patient"], patient_options)
                                    eid = _safe_resolve_id(st.session_state["selected_exercise"], exercise_options)
                                    nts = st.session_state["notes"]
                                    sr = st.session_state.get("sampling_rate", 0.0)
                                    gen_raw = st.session_state.get("generate_raw", False)
                                    gen_mp = st.session_state.get("generate_mediapipe", False)
                                    gen_leg = st.session_state.get("generate_legacy", True)

                                    # Usar FPS original del video
                                    original_fps = cap.fps
                                    st.info(f"Procesando video: {original_fps:.1f} fps")

                                    sess = SessionManager(
                                        base_name="analisis_video",
                                        patient_id=pid,
                                        exercise_id=eid,
                                        notes=nts,
                                        sampling_rate=sr,
                                        generate_raw=gen_raw,
                                        generate_mediapipe=gen_mp,
                                        generate_legacy=gen_leg,
                                    )
                                    sid = sess.start_session(cap.width, cap.height, original_fps)

                                    detector = PoseDetector()
                                    total_frames = int(cap.cap.get(cv2.CAP_PROP_FRAME_COUNT)) or 1
                                    prog = st.progress(0)
                                    idx = 0

                                    while True:
                                        ret, frame = cap.read_frame()
                                        if not ret:
                                            break

                                        h, w = frame.shape[:2]
                                        
                                        sequence_num = sess.get_sequence_counter()
                                        
                                        # Frame RAW
                                        frame_raw = None
                                        if gen_raw:
                                            frame_raw = frame.copy()
                                            _draw_sequence_text(frame_raw, sequence_num)
                                        
                                        # Procesamiento
                                        image_bgr, results = detector.process_frame(frame)
                                        
                                        # Frame MediaPipe
                                        frame_mediapipe = None
                                        if gen_mp:
                                            if results and results.pose_landmarks:
                                                frame_mediapipe = detector.draw_mediapipe_on_white_background(
                                                    w, h, results, sequence=sequence_num
                                                )
                                            else:
                                                frame_mediapipe = np.ones((h, w, 3), dtype=np.uint8) * 255
                                                _draw_sequence_text(frame_mediapipe, sequence_num)
                                        
                                        # Frame Legacy
                                        frame_legacy = None
                                        if gen_leg:
                                            frame_legacy = image_bgr.copy()
                                            if results and results.pose_landmarks:
                                                lm = detector.extract_landmarks(results)
                                                joint_data, angles = _extract_joint_data(lm, w, h)
                                                
                                                if joint_data:
                                                    frame_legacy = draw_legacy_overlay(
                                                        frame_legacy, lm, w, h,
                                                        angles=angles,
                                                        a_max=60.0,
                                                        sequence=sequence_num
                                                    )
                                                    
                                                    try:
                                                        sess.record_frame_data(
                                                            frame_index=idx,
                                                            elapsed_time=sess.elapsed_time(),
                                                            joints=joint_data
                                                        )
                                                    except Exception as e:
                                                        print(f"Error al registrar frame {idx}: {e}")
                                                else:
                                                    _draw_sequence_text(frame_legacy, sequence_num)
                                            else:
                                                _draw_sequence_text(frame_legacy, sequence_num)

                                        sess.write_video_frames(
                                            frame_raw=frame_raw,
                                            frame_mediapipe=frame_mediapipe,
                                            frame_legacy=frame_legacy
                                        )
                                        
                                        idx += 1
                                        prog.progress(min(idx / total_frames, 1.0))

                                    sess.close_session()
                                    cap.release()
                                    detector.release()
                                    
                                    # Limpiar archivo temporal
                                    try:
                                        Path(temp_path).unlink()
                                    except:
                                        pass
                                    
                                    raw_path, mp_path, leg_path = sess.get_video_paths()
                                    st.success(f"Sesión guardada (ID {sid})")
                                    if raw_path: st.info(f"RAW: {os.path.basename(raw_path)}")
                                    if mp_path: st.info(f"MediaPipe: {os.path.basename(mp_path)}")
                                    if leg_path: st.info(f"Clínico: {os.path.basename(leg_path)}")
                                    
                                    st.session_state.validation_result = None
                                    _reset_record_ui_state()
                                    st.rerun()
                            
                            with col_cancel:
                                if st.button("Cancelar", use_container_width=True):
                                    # Limpiar temporal
                                    try:
                                        Path(result['temp_path']).unlink()
                                    except:
                                        pass
                                    st.session_state.validation_result = None
                                    _reset_record_ui_state()
                                    st.rerun()
                    else:
                        st.error(f"Video inválido: {result['message']}")
                        
                        # Mostrar metadata si está disponible
                        if result['metadata']:
                            with st.expander("Detalles técnicos"):
                                st.json(result['metadata'])
                        
                        if st.button("Intentar con otro archivo"):
                            # Limpiar temporal
                            try:
                                Path(result['temp_path']).unlink()
                            except:
                                pass
                            st.session_state.validation_result = None
                            st.rerun()