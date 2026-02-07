import sys
import os
import streamlit as st

if getattr(sys, 'frozen', False):
    application_path = sys._MEIPASS
else:
    application_path = os.path.dirname(os.path.abspath(__file__))
    parent_dir = os.path.abspath(os.path.join(application_path, ".."))
    if parent_dir not in sys.path:
        sys.path.insert(0, parent_dir)

from db.init_db import ensure_database_exists
ensure_database_exists()

from ui.components import charts, patients, exercises, sessions, reports, feedback

st.set_page_config(
    page_title="Recon IA - Clínica",
    page_icon="🩺",
    layout="wide"
)

def main():
    st.sidebar.title("🩺 Navegación principal")
    menu = ["Inicio", "Pacientes", "Ejercicios", "Sesiones", "Historial y métricas", "Feedback"]
    choice = st.sidebar.radio("Ir a:", menu)

    try:
        if choice == "Inicio":
            charts.app()

        elif choice == "Pacientes":
            patients.app()

        elif choice == "Ejercicios":
            exercises.app()

        elif choice == "Sesiones":
            sessions.app()

        elif choice == "Historial y métricas":
            reports.app()

        elif choice == "Feedback":
            feedback.app()

        else:
            st.error("⚠️ Opción no válida seleccionada.")

    except Exception as e:
        st.error("❌ Ha ocurrido un error inesperado al cargar la sección.")
        st.exception(e)

if __name__ == "__main__":
    main()