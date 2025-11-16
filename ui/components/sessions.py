# ui/components/sessions.py
import os
import tempfile
import datetime
import cv2
import streamlit as st

# Core
from core.pose_detection import PoseDetector
from core.angle_calculator import calculate_angle
from core.session_manager import SessionManager
from core.video_capture import VideoCaptureManager
from core.legacy_overlay import draw_legacy_overlay

# CRUD
from db import crud

# -------------------------------------------------------------
# WebRTC opcional (webcam en navegador). Si no está, se desactiva.
# -------------------------------------------------------------
_WEBRTC_OK = True
try:
    from streamlit_webrtc import webrtc_streamer, VideoProcessorBase, WebRtcMode, RTCConfiguration
    import av
except Exception:
    _WEBRTC_OK = False


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
    st.session_state.setdefault("sampling_rate", 0.0)  # NUEVO


def _overlay_rec(image_bgr, paused=False, landmarks_found=False):
    color = (0, 0, 255) if not paused else (0, 165, 255)
    cv2.circle(image_bgr, (30, 30), 10, color, -1)
    label = "REC" if not paused else "PAUSA"
    cv2.putText(image_bgr, label, (50, 36), cv2.FONT_HERSHEY_SIMPLEX, 0.8, color, 2)
    txt = "LMK: OK" if landmarks_found else "LMK: --"
    cv2.putText(image_bgr, txt, (30, 66), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (200, 200, 200), 2)
    return image_bgr


def _reset_record_ui_state():
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
    Extrae TODOS los datos biomecánicos necesarios (brazos, piernas, PIES).
    
    Returns:
        dict con coordenadas en píxeles y ángulos calculados
    """
    try:
        # Brazo derecho
        shoulder_r = (lm["RIGHT_SHOULDER"][0] * w, lm["RIGHT_SHOULDER"][1] * h)
        elbow_r = (lm["RIGHT_ELBOW"][0] * w, lm["RIGHT_ELBOW"][1] * h)
        wrist_r = (lm["RIGHT_WRIST"][0] * w, lm["RIGHT_WRIST"][1] * h)
        
        # Brazo izquierdo
        shoulder_l = (lm["LEFT_SHOULDER"][0] * w, lm["LEFT_SHOULDER"][1] * h)
        elbow_l = (lm["LEFT_ELBOW"][0] * w, lm["LEFT_ELBOW"][1] * h)
        wrist_l = (lm["LEFT_WRIST"][0] * w, lm["LEFT_WRIST"][1] * h)
        
        # Pierna derecha
        hip_r = (lm["RIGHT_HIP"][0] * w, lm["RIGHT_HIP"][1] * h)
        knee_r = (lm["RIGHT_KNEE"][0] * w, lm["RIGHT_KNEE"][1] * h)
        ankle_r = (lm["RIGHT_ANKLE"][0] * w, lm["RIGHT_ANKLE"][1] * h)
        
        # Pierna izquierda
        hip_l = (lm["LEFT_HIP"][0] * w, lm["LEFT_HIP"][1] * h)
        knee_l = (lm["LEFT_KNEE"][0] * w, lm["LEFT_KNEE"][1] * h)
        ankle_l = (lm["LEFT_ANKLE"][0] * w, lm["LEFT_ANKLE"][1] * h)
        
        # NUEVO: Pies
        heel_r = (lm["RIGHT_HEEL"][0] * w, lm["RIGHT_HEEL"][1] * h)
        foot_index_r = (lm["RIGHT_FOOT_INDEX"][0] * w, lm["RIGHT_FOOT_INDEX"][1] * h)
        heel_l = (lm["LEFT_HEEL"][0] * w, lm["LEFT_HEEL"][1] * h)
        foot_index_l = (lm["LEFT_FOOT_INDEX"][0] * w, lm["LEFT_FOOT_INDEX"][1] * h)
        
        # Calcular ángulos
        angles = {
            "angle_arm_r": calculate_angle(shoulder_r, elbow_r, wrist_r),
            "angle_arm_l": calculate_angle(shoulder_l, elbow_l, wrist_l),
            "angle_leg_r": calculate_angle(hip_r, knee_r, ankle_r),
            "angle_leg_l": calculate_angle(hip_l, knee_l, ankle_l),
        }
        
        # Retornar TODO
        return {
            # Brazos
            "shoulder_x_r": shoulder_r[0], "shoulder_y_r": shoulder_r[1],
            "elbow_x_r": elbow_r[0], "elbow_y_r": elbow_r[1],
            "wrist_x_r": wrist_r[0], "wrist_y_r": wrist_r[1],
            "angle_arm_r": angles["angle_arm_r"],
            
            "shoulder_x_l": shoulder_l[0], "shoulder_y_l": shoulder_l[1],
            "elbow_x_l": elbow_l[0], "elbow_y_l": elbow_l[1],
            "wrist_x_l": wrist_l[0], "wrist_y_l": wrist_l[1],
            "angle_arm_l": angles["angle_arm_l"],
            
            # Piernas
            "hip_x_r": hip_r[0], "hip_y_r": hip_r[1],
            "knee_x_r": knee_r[0], "knee_y_r": knee_r[1],
            "ankle_x_r": ankle_r[0], "ankle_y_r": ankle_r[1],
            "angle_leg_r": angles["angle_leg_r"],
            
            "hip_x_l": hip_l[0], "hip_y_l": hip_l[1],
            "knee_x_l": knee_l[0], "knee_y_l": knee_l[1],
            "ankle_x_l": ankle_l[0], "ankle_y_l": ankle_l[1],
            "angle_leg_l": angles["angle_leg_l"],
            
            # NUEVO: Pies
            "heel_x_r": heel_r[0], "heel_y_r": heel_r[1],
            "foot_index_x_r": foot_index_r[0], "foot_index_y_r": foot_index_r[1],
            "heel_x_l": heel_l[0], "heel_y_l": heel_l[1],
            "foot_index_x_l": foot_index_l[0], "foot_index_y_l": foot_index_l[1],
        }, angles
        
    except KeyError:
        return None, {}


# ============================================================
# Procesador WebRTC
# ============================================================
class Processor(VideoProcessorBase):
    """Procesador de vídeo para streamlit-webrtc con captura completa de datos."""
    
    def __init__(self, patient_id, exercise_id, notes, sampling_rate=0.0):
        self.patient_id = patient_id
        self.exercise_id = exercise_id
        self.notes = notes
        self.sampling_rate = sampling_rate

        self.detector = PoseDetector()
        self.session_mgr: SessionManager | None = None
        self.frame_idx = 0
        self.started = False

    def _ensure_session(self, w: int, h: int, fps_hint: int = 30):
        if not self.started:
            self.session_mgr = SessionManager(
                output_dir="data/exports",
                base_name="captura_webcam",
                patient_id=self.patient_id,
                exercise_id=self.exercise_id,
                notes=self.notes,
                sampling_rate=self.sampling_rate,  # NUEVO
            )
            self.sid = self.session_mgr.start_session(w, h, fps_hint)
            self.started = True

    def recv(self, frame: "av.VideoFrame") -> "av.VideoFrame":
        img_bgr = frame.to_ndarray(format="bgr24")
        h, w = img_bgr.shape[:2]

        # Sesión al primer frame
        self._ensure_session(w, h, fps_hint=30)

        # Procesamiento
        image_bgr, results = self.detector.process_frame(img_bgr)
        landmarks_found = bool(results and results.pose_landmarks)

        if landmarks_found:
            lm = self.detector.extract_landmarks(results)
            
            # NUEVO: Usar función centralizada
            joint_data, angles = _extract_joint_data(lm, w, h)
            
            if joint_data:
                # Dibujo "legacy" con info de frame
                image_bgr = draw_legacy_overlay(
                    image_bgr, lm, w, h,
                    angles=angles,
                    a_max=60.0,
                    frame_idx=self.frame_idx,  # NUEVO
                    fps=30  # NUEVO
                )

                # Registro en BD (solo si no está en pausa)
                if self.session_mgr and not st.session_state.get("paused", False):
                    try:
                        self.session_mgr.record_frame_data(
                            frame_index=self.frame_idx,
                            elapsed_time=self.session_mgr.elapsed_time(),
                            joints=joint_data
                        )
                    except Exception:
                        pass

                    self.session_mgr.write_video_frame(image_bgr)
                    self.frame_idx += 1

        # Overlay REC/PAUSA
        image_bgr = _overlay_rec(image_bgr, 
                                 paused=st.session_state.get("paused", False), 
                                 landmarks_found=landmarks_found)
        return av.VideoFrame.from_ndarray(image_bgr, format="bgr24")

    def close_and_save(self):
        if self.session_mgr:
            self.session_mgr.close_session()
            return self.session_mgr.session_id, self.session_mgr.video_path
        return None, None

    def close_and_discard(self):
        sid, vid = None, None
        if self.session_mgr:
            sid = self.session_mgr.session_id
            vid = self.session_mgr.video_path
            try:
                self.session_mgr.close_session()
            except Exception:
                pass
            if sid:
                try:
                    crud.delete_session(sid)
                except Exception:
                    pass
            if vid and os.path.exists(vid):
                try:
                    os.remove(vid)
                except Exception:
                    pass
        return sid, vid

    def release_models(self):
        try:
            self.detector.release()
        except Exception:
            pass


# ============================================================
# APP
# ============================================================
def app():
    _init_state()

    st.title("Gestión de Sesiones")
    st.write("Cree nuevas sesiones de análisis, revise grabaciones y consulte métricas registradas.")

    # Datos base
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

    # Formulario de inicio
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
        
        # NUEVO: Opción de sampling rate
        col_adv = st.columns(2)
        with col_adv[0]:
            use_sampling = st.checkbox("Reducir frecuencia de muestreo", 
                                      help="Guarda menos frames en BD para ahorrar espacio")
        with col_adv[1]:
            if use_sampling:
                sampling_rate = st.slider("Segundos entre muestras", 0.1, 1.0, 0.2, 0.05)
            else:
                sampling_rate = 0.0

        if source_mode == "Webcam (WebRTC)" and not _WEBRTC_OK:
            st.info("Para usar la webcam en el navegador: `pip install streamlit-webrtc av`")

        start_btn = st.form_submit_button("Iniciar")

        if start_btn:
            st.session_state["selected_patient"] = selected_patient
            st.session_state["selected_exercise"] = selected_exercise
            st.session_state["notes"] = notes
            st.session_state["source_mode"] = source_mode
            st.session_state["sampling_rate"] = sampling_rate  # NUEVO
            st.session_state["record_mode"] = True
            st.session_state["paused"] = False
            st.session_state["save_prompt"] = False
            st.rerun()

    # ============================================================
    # 1) Webcam (WebRTC)
    # ============================================================
    if st.session_state.get("record_mode") and st.session_state.get("source_mode") == "Webcam (WebRTC)":
        if not _WEBRTC_OK:
            st.error("streamlit-webrtc no está instalado.")
            return

        st.subheader("Grabación con webcam (en vivo)")
        ctrl_cols = st.columns([1, 1, 3])
        with ctrl_cols[0]:
            if st.button("Pausar" if not st.session_state["paused"] else "Reanudar"):
                st.session_state["paused"] = not st.session_state["paused"]
        with ctrl_cols[1]:
            if st.button("Detener"):
                st.session_state["save_prompt"] = True
                st.session_state["paused"] = True

        try:
            rtc_configuration = RTCConfiguration(
                {"iceServers": [{"urls": ["stun:stun.l.google.com:19302"]}]}
            )
        except Exception:
            rtc_configuration = {"iceServers": [{"urls": ["stun:stun.l.google.com:19302"]}]}

        pid = _safe_resolve_id(st.session_state["selected_patient"], patient_options)
        eid = _safe_resolve_id(st.session_state["selected_exercise"], exercise_options)
        nts = st.session_state["notes"]
        sr = st.session_state.get("sampling_rate", 0.0)  # NUEVO

        ctx = webrtc_streamer(
            key="recon-ia-webrtc",
            mode=WebRtcMode.SENDRECV,
            rtc_configuration=rtc_configuration,
            media_stream_constraints={"video": True, "audio": False},
            video_processor_factory=lambda: Processor(pid, eid, nts, sr),  # NUEVO: pasar sampling_rate
            async_processing=True,
        )

        # Diálogo Guardar/Descartar
        if st.session_state.get("save_prompt"):
            st.warning("¿Desea guardar esta sesión?")
            bcols = st.columns(3)
            with bcols[0]:
                if st.button("Guardar sesión"):
                    if ctx and ctx.video_processor:
                        sid, vpath = ctx.video_processor.close_and_save()
                        ctx.video_processor.release_models()
                        try:
                            ctx.stop()
                        except Exception:
                            pass
                        if sid:
                            st.success(f"Sesión guardada (ID {sid}).")
                    _reset_record_ui_state()
                    st.rerun()

            with bcols[1]:
                if st.button("Descartar sesión"):
                    if ctx and ctx.video_processor:
                        sid, vpath = ctx.video_processor.close_and_discard()
                        ctx.video_processor.release_models()
                        try:
                            ctx.stop()
                        except Exception:
                            pass
                    st.info("Sesión descartada.")
                    _reset_record_ui_state()
                    st.rerun()

            with bcols[2]:
                if st.button("Cancelar"):
                    st.session_state["save_prompt"] = False
                    st.session_state["paused"] = False
                    st.rerun()

    # ============================================================
    # 2) Subir vídeo (análisis batch)
    # ============================================================
    if st.session_state.get("record_mode") and st.session_state.get("source_mode") == "Subir vídeo":
        st.subheader("Análisis desde archivo de vídeo")
        uploaded = st.file_uploader("Seleccione un archivo (MP4/MOV/AVI)", type=["mp4", "mov", "avi"])

        if uploaded is None:
            st.info("Suba un vídeo para analizar y guardar la sesión.")
        else:
            if st.button("Analizar y guardar"):
                os.makedirs("recordings", exist_ok=True)
                with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4", dir="recordings") as tmp:
                    tmp.write(uploaded.getvalue())
                    input_path = tmp.name

                try:
                    cap = VideoCaptureManager(input_path)
                except Exception as e:
                    st.error(f"No se pudo abrir el vídeo: {e}")
                    return

                pid = _safe_resolve_id(st.session_state["selected_patient"], patient_options)
                eid = _safe_resolve_id(st.session_state["selected_exercise"], exercise_options)
                nts = st.session_state["notes"]
                sr = st.session_state.get("sampling_rate", 0.0)

                sess = SessionManager(
                    output_dir="data/exports",
                    base_name="analisis_video",
                    patient_id=pid,
                    exercise_id=eid,
                    notes=nts,
                    sampling_rate=sr,  # NUEVO
                )
                sid = sess.start_session(cap.width, cap.height, cap.fps)

                detector = PoseDetector()
                total_frames = int(cap.cap.get(cv2.CAP_PROP_FRAME_COUNT)) or 1
                prog = st.progress(0)
                idx = 0

                while True:
                    ret, frame = cap.read_frame()
                    if not ret:
                        break

                    image_bgr, results = detector.process_frame(frame)
                    h, w = image_bgr.shape[:2]

                    if results and results.pose_landmarks:
                        lm = detector.extract_landmarks(results)
                        
                        # NUEVO: Usar función centralizada
                        joint_data, angles = _extract_joint_data(lm, w, h)
                        
                        if joint_data:
                            # Dibujo legacy con info
                            image_bgr = draw_legacy_overlay(
                                image_bgr, lm, w, h,
                                angles=angles,
                                a_max=60.0,
                                frame_idx=idx,  # NUEVO
                                fps=cap.fps  # NUEVO
                            )

                            # Registrar
                            try:
                                sess.record_frame_data(
                                    frame_index=idx,
                                    elapsed_time=sess.elapsed_time(),
                                    joints=joint_data
                                )
                            except Exception:
                                pass

                    sess.write_video_frame(image_bgr)
                    idx += 1
                    prog.progress(min(idx / total_frames, 1.0))

                sess.close_session()
                cap.release()
                detector.release()
                st.success(f"Sesión guardada (ID {sid}). Vídeo: {sess.video_path}")
                _reset_record_ui_state()
                st.rerun()

    # ============================================================
    # 3) Listado de sesiones
    # ============================================================
    st.divider()
    st.subheader("Sesiones registradas")

    try:
        sessions = crud.get_all_sessions()
    except Exception as e:
        st.error(f"Error al obtener sesiones: {e}")
        return

    if not sessions:
        st.info("Aún no hay sesiones registradas.")
        return

    for s in sessions:
        sid = s.get("id")
        timestamp = s.get("datetime")
        patient_name = s.get("patient_name")
        exercise_name = s.get("exercise_name")
        video_path = s.get("video_path")
        notes = s.get("notes")

        with st.expander(f"Sesión ID {sid} — {patient_name} / {exercise_name}"):
            st.markdown(f"**Fecha:** {timestamp or datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            st.markdown(f"**Paciente:** {patient_name}")
            st.markdown(f"**Ejercicio:** {exercise_name}")
            st.markdown(f"**Notas:** {notes or '—'}")
            if video_path and os.path.exists(video_path):
                st.video(video_path)
            else:
                st.warning("Vídeo no disponible.")

            c1, c2 = st.columns(2)
            with c1:
                if st.button("Ver métricas", key=f"metrics_{sid}"):
                    metrics = crud.get_metrics_by_session(sid)
                    if not metrics:
                        st.info("No se encontraron métricas para esta sesión.")
                    else:
                        for m in metrics:
                            st.write(f"- {m[0]}: {m[1]} {m[2] or ''}")
            with c2:
                if st.button("Eliminar sesión", key=f"delete_{sid}"):
                    st.session_state["delete_candidate"] = sid

                if st.session_state.get("delete_candidate") == sid:
                    st.warning(f"¿Seguro que desea eliminar la sesión {sid}?")
                    cc = st.columns(3)
                    with cc[0]:
                        if st.button("Confirmar", key=f"confirm_{sid}"):
                            deleted = crud.delete_session(sid)
                            if deleted:
                                st.success(f"Sesión {sid} eliminada.")
                            try:
                                if video_path and os.path.exists(video_path):
                                    os.remove(video_path)
                            except Exception:
                                pass
                            st.session_state.pop("delete_candidate", None)
                            st.rerun()
                    with cc[1]:
                        if st.button("Cancelar", key=f"cancel_{sid}"):
                            st.session_state.pop("delete_candidate", None)
                            st.info("Eliminación cancelada.")
                            st.rerun()