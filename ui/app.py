import sys
import os
import streamlit as st

# ============================================================
# Ajuste de ruta para importar módulos locales (PyInstaller compatible)
# ============================================================
if getattr(sys, 'frozen', False):
    # Ejecutando como ejecutable empaquetado
    application_path = sys._MEIPASS
else:
    # Ejecutando como script normal
    application_path = os.path.dirname(os.path.abspath(__file__))
    # Agregar directorio padre para imports relativos
    parent_dir = os.path.abspath(os.path.join(application_path, ".."))
    if parent_dir not in sys.path:
        sys.path.insert(0, parent_dir)

# ============================================================
# Inicialización de la base de datos
# ============================================================
from db.init_db import ensure_database_exists
ensure_database_exists()

from ui.components import charts, patients, exercises, sessions, reports

# ============================================================
# Configuración general de la aplicación
# ============================================================
st.set_page_config(
    page_title="Recon IA - Clínica",
    page_icon="🩺",
    layout="wide"
)

# ============================================================
# Interfaz principal
# ============================================================
def main():
    st.sidebar.title("🩺 Navegación principal")
    menu = ["Inicio", "Pacientes", "Ejercicios", "Sesiones", "Historial y métricas"]
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

        else:
            st.error("⚠️ Opción no válida seleccionada.")

    except Exception as e:
        st.error("❌ Ha ocurrido un error inesperado al cargar la sección.")
        st.exception(e)  # Muestra el traceback completo para depuración

# ============================================================
# Punto de entrada
# ============================================================
if __name__ == "__main__":
    main()