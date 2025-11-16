# ui/components/reports.py
from pathlib import Path
from datetime import date
import pandas as pd
import streamlit as st

from db import crud
from reports.pdf_report import generate_session_report_pdf
from datetime import date
import pandas as pd
# === Utilidades ===

ROOT_DIR = Path(__file__).resolve().parents[2]  # raíz del proyecto (…/recon_ia)

def _resolve_video_path(video_path: str) -> Path | None:
    """Intenta resolver la ruta del vídeo de forma robusta."""
    if not video_path:
        return None
    p = Path(video_path)
    if p.is_absolute() and p.exists():
        return p
    for c in (ROOT_DIR / p, Path.cwd() / p):
        if c.exists():
            return c
    return None


def _load_filters():
    patients = crud.get_all_patients()
    exercises = crud.get_all_exercises()

    patient_options = {p[1]: p[0] for p in patients} if patients else {}
    exercise_options = {e[1]: e[0] for e in exercises} if exercises else {}

    with st.form("filter_form"):
        st.subheader("Filtros")
        selected_patient = st.selectbox(
            "Paciente",
            options=["Todos"] + list(patient_options.keys()) if patient_options else ["No hay pacientes"]
        )
        selected_exercise = st.selectbox(
            "Ejercicio",
            options=["Todos"] + list(exercise_options.keys()) if exercise_options else ["No hay ejercicios"]
        )
        date_range = st.date_input("Rango de fechas", [])  # [] -> sin filtro inicialmente
        apply_filters = st.form_submit_button("Aplicar filtros")

    return patient_options, exercise_options, selected_patient, selected_exercise, date_range, apply_filters


def _filter_sessions(sessions, selected_patient, selected_exercise, date_range):
    filtered = list(sessions)  # copia defensiva

    if selected_patient not in ("Todos", "No hay pacientes"):
        filtered = [s for s in filtered if s.get("patient_name") == selected_patient]

    if selected_exercise not in ("Todos", "No hay ejercicios"):
        filtered = [s for s in filtered if s.get("exercise_name") == selected_exercise]

    # --- Rango de fechas robusto: acepta lista o tupla y pd.Timestamp ---
    start_date = end_date = None
    if isinstance(date_range, (list, tuple)) and len(date_range) == 2:
        d0, d1 = date_range
        # Normalizar a datetime.date
        if hasattr(d0, "date"):  # pd.Timestamp o datetime
            d0 = d0.date()
        if hasattr(d1, "date"):
            d1 = d1.date()
        if isinstance(d0, date) and isinstance(d1, date):
            start_date, end_date = d0, d1

    if start_date and end_date:
        def _in_range(dt_str: str) -> bool:
            dt = pd.to_datetime(dt_str, errors="coerce")
            return pd.notna(dt) and start_date <= dt.date() <= end_date

        filtered = [s for s in filtered if s.get("datetime") and _in_range(s["datetime"])]

    return filtered

# === Página ===

def app():
    st.title("Historial y métricas")
    st.write("Filtra sesiones y descarga el informe PDF de la sesión seleccionada.")

    # Filtros
    patient_options, exercise_options, selected_patient, selected_exercise, date_range, apply_filters = _load_filters()

    # Cargar sesiones
    try:
        sessions = crud.get_all_sessions()
    except Exception as err:
        st.error(f"Error al obtener sesiones: {err}")
        return

    if not sessions:
        st.info("No se encontraron sesiones.")
        return

    # Aplicar filtros
    filtered_sessions = _filter_sessions(sessions, selected_patient, selected_exercise, date_range)

    # Tabla con sesiones filtradas
    st.subheader("Sesiones filtradas")
    if not filtered_sessions:
        st.info("No se encontraron sesiones con los filtros aplicados.")
        return

    st.dataframe(
        pd.DataFrame([{
            "ID": s.get("id", ""),
            "Fecha y hora": s.get("datetime", ""),
            "Paciente": s.get("patient_name", "Desconocido"),
            "Ejercicio": s.get("exercise_name", "Desconocido"),
            "Vídeo": s.get("video_path") or "—",
        } for s in filtered_sessions]),
        use_container_width=True
    )

    # Detalle de cada sesión
    for s in filtered_sessions:
        sid = s.get("id")
        ts = s.get("datetime")
        patient_name = s.get("patient_name") or "—"
        exercise_name = s.get("exercise_name") or "—"
        video_path = s.get("video_path") or ""
        notes = s.get("notes") or "—"

        with st.expander(f"Sesión ID {sid} — {patient_name} / {exercise_name}"):
            st.markdown(f"**Fecha:** {ts or '—'}")
            st.markdown(f"**Paciente:** {patient_name}")
            st.markdown(f"**Ejercicio:** {exercise_name}")
            st.markdown(f"**Notas:** {notes}")

            # Vídeo
            abs_video = _resolve_video_path(video_path)
            if abs_video:
                st.video(str(abs_video))
                st.caption(str(abs_video))
            else:
                st.warning("Vídeo no encontrado en disco.")
                if video_path:
                    st.code(video_path)

            # Métricas
            st.markdown("**Métricas:**")
            try:
                metrics = crud.get_metrics_by_session(sid)
            except Exception as e:
                metrics = []
                st.error(f"No se pudieron cargar las métricas: {e}")

            if metrics:
                for m in metrics:
                    name, value, unit = m[0], m[1], m[2] or ""
                    st.write(f"- {name}: {value} {unit}".strip())
            else:
                st.info("Sin métricas para esta sesión.")

            # --- Generar y descargar PDF ---
            gen_key = f"gen_pdf_{sid}"
            dl_key = f"dl_pdf_{sid}"

            if st.button(f"Generar informe PDF (sesión {sid})", key=gen_key):
                try:
                    pdf_bytes = generate_session_report_pdf(int(sid))
                    fname = f"informe_sesion_{sid}.pdf"
                    st.download_button(
                        "Descargar informe PDF",
                        data=pdf_bytes,
                        file_name=fname,
                        mime="application/pdf",
                        key=dl_key
                    )
                    st.success("Informe generado correctamente.")
                except Exception as e:
                    st.error(f"No se pudo generar el informe: {e}")