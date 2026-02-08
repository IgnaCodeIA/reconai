import os
import datetime
from datetime import date
import streamlit as st
import pandas as pd

from db import crud
from reports.pdf_report import generate_session_report_pdf


def _resolve_video_path(relative_path):
    if not relative_path:
        return None
    
    if os.path.isabs(relative_path) and os.path.exists(relative_path):
        return relative_path
    
    cwd_path = os.path.join(os.getcwd(), relative_path)
    if os.path.exists(cwd_path):
        return cwd_path
    
    root_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    root_path = os.path.join(root_dir, relative_path)
    if os.path.exists(root_path):
        return root_path
    
    return None


def _filter_sessions(sessions, selected_patient, selected_exercise, date_range):
    filtered = list(sessions)
    
    if selected_patient not in ("Todos", "No hay pacientes"):
        filtered = [s for s in filtered if s.get("patient_name") == selected_patient]
    
    if selected_exercise not in ("Todos", "No hay ejercicios"):
        filtered = [s for s in filtered if s.get("exercise_name") == selected_exercise]
    
    start_date = end_date = None
    if isinstance(date_range, (list, tuple)) and len(date_range) == 2:
        d0, d1 = date_range
        d0 = d0.date() if hasattr(d0, "date") else d0
        d1 = d1.date() if hasattr(d1, "date") else d1
        if isinstance(d0, date) and isinstance(d1, date):
            start_date, end_date = d0, d1
    
    if start_date and end_date:
        def _in_range(dt_str):
            dt = pd.to_datetime(dt_str, errors="coerce")
            return pd.notna(dt) and start_date <= dt.date() <= end_date
        
        filtered = [s for s in filtered if s.get("datetime") and _in_range(s["datetime"])]
    
    return filtered


def app():
    st.title("Historial y Métricas")
    st.write("Consulte el histórico de sesiones, visualice vídeos y genere informes PDF.")

    st.subheader("Filtros")
    
    try:
        patients = crud.get_all_patients()
        exercises = crud.get_all_exercises()
        sessions = crud.get_all_sessions()
    except Exception as e:
        st.error(f"Error al cargar datos: {e}")
        return

    patient_names = ["Todos"] + ([p[1] for p in patients] if patients else ["No hay pacientes"])
    exercise_names = ["Todos"] + ([e[1] for e in exercises] if exercises else ["No hay ejercicios"])

    col_filt = st.columns(3)
    with col_filt[0]:
        selected_patient = st.selectbox("Paciente", patient_names)
    with col_filt[1]:
        selected_exercise = st.selectbox("Ejercicio", exercise_names)
    with col_filt[2]:
        date_range = st.date_input(
            "Rango de fechas",
            value=(datetime.date.today() - datetime.timedelta(days=30), datetime.date.today()),
            max_value=datetime.date.today()
        )

    filtered_sessions = _filter_sessions(sessions, selected_patient, selected_exercise, date_range)

    st.info(f"{len(filtered_sessions)} sesión(es) encontrada(s)")

    if not filtered_sessions:
        st.warning("No hay sesiones que coincidan con los filtros.")
        return

    st.divider()
    st.subheader("Sesiones")

    for s in filtered_sessions:
        sid = s.get("id")
        timestamp = s.get("datetime")
        patient_name = s.get("patient_name")
        exercise_name = s.get("exercise_name")
        notes = s.get("notes")
        
        video_path_raw = s.get("video_path_raw")
        video_path_mediapipe = s.get("video_path_mediapipe")
        video_path_legacy = s.get("video_path_legacy")

        with st.expander(f"Sesión {sid} — {patient_name} / {exercise_name} — {timestamp}"):
            st.markdown(f"**Paciente:** {patient_name}")
            st.markdown(f"**Ejercicio:** {exercise_name}")
            st.markdown(f"**Fecha:** {timestamp}")
            st.markdown(f"**Notas:** {notes or '—'}")

            st.markdown("---")
            st.markdown("### Visualización de vídeo")
            
            available_videos = {}
            
            raw_resolved = _resolve_video_path(video_path_raw)
            if raw_resolved:
                available_videos["Sin procesar (RAW)"] = raw_resolved
            
            mp_resolved = _resolve_video_path(video_path_mediapipe)
            if mp_resolved:
                available_videos["MediaPipe completo"] = mp_resolved
            
            leg_resolved = _resolve_video_path(video_path_legacy)
            if leg_resolved:
                available_videos["Overlay clínico"] = leg_resolved
            
            if not available_videos:
                st.warning("No hay vídeos disponibles para esta sesión")
            else:
                selected_version = st.radio(
                    "Seleccione versión a visualizar:",
                    list(available_videos.keys()),
                    key=f"video_selector_{sid}",
                    horizontal=True
                )
                
                video_path = available_videos[selected_version]
                st.video(video_path)
                st.caption(f"{os.path.basename(video_path)}")

            st.markdown("---")
            col_actions = st.columns(3)
            
            with col_actions[0]:
                if st.button("Ver métricas", key=f"metrics_{sid}"):
                    metrics = crud.get_metrics_by_session(sid)
                    if not metrics:
                        st.info("No se encontraron métricas para esta sesión.")
                    else:
                        st.markdown("**Métricas registradas:**")
                        for m in metrics:
                            st.write(f"- {m[0]}: {m[1]:.2f} {m[2] or ''}")
            
            with col_actions[1]:
                if st.button("Generar PDF", key=f"pdf_{sid}"):
                    try:
                        pdf_bytes = generate_session_report_pdf(sid)
                        st.download_button(
                            label="Descargar informe PDF",
                            data=pdf_bytes,
                            file_name=f"informe_sesion_{sid}.pdf",
                            mime="application/pdf",
                            key=f"dl_pdf_{sid}",
                        )
                    except Exception as e:
                        st.error(f"Error al generar PDF: {e}")
            
            with col_actions[2]:
                if st.button("Eliminar", key=f"delete_{sid}"):
                    st.session_state[f"delete_confirm_{sid}"] = True
                
                if st.session_state.get(f"delete_confirm_{sid}", False):
                    st.warning(f"¿Confirmar eliminación de sesión {sid}?")
                    cc = st.columns(2)
                    with cc[0]:
                        if st.button("Sí", key=f"yes_{sid}"):
                            crud.delete_session(sid)
                            for path in [video_path_raw, video_path_mediapipe, video_path_legacy]:
                                resolved = _resolve_video_path(path)
                                if resolved:
                                    try:
                                        os.remove(resolved)
                                    except Exception:
                                        pass
                            st.success(f"Sesión {sid} eliminada")
                            st.session_state.pop(f"delete_confirm_{sid}", None)
                            st.rerun()
                    with cc[1]:
                        if st.button("No", key=f"no_{sid}"):
                            st.session_state.pop(f"delete_confirm_{sid}", None)
                            st.rerun()