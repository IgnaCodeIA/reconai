import streamlit as st
import pandas as pd
from db import crud


def app():
    """
    Dashboard principal de inicio para Recon IA.
    Muestra métricas globales y sesiones recientes.
    """
    st.title("🏠 Panel de inicio")
    st.markdown("### Bienvenido al sistema de análisis biomecánico **Recon IA**")

    # ============================================================
    # MÉTRICAS GLOBALES
    # ============================================================
    try:
        counts = crud.get_table_counts()
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Pacientes", counts.get("patients", 0))
        col2.metric("Ejercicios", counts.get("exercises", 0))
        col3.metric("Sesiones", counts.get("sessions", 0))
        col4.metric("Métricas", counts.get("metrics", 0))
    except Exception as e:
        st.error(f"❌ Error al cargar métricas globales: {e}")
        return

    st.divider()

    # ============================================================
    # SESIONES RECIENTES
    # ============================================================
    st.subheader("🕓 Sesiones recientes")

    try:
        conn = crud.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT s.id, s.timestamp, p.name AS paciente, e.name AS ejercicio
            FROM sessions s
            LEFT JOIN patients p ON s.patient_id = p.id
            LEFT JOIN exercises e ON s.exercise_id = e.id
            ORDER BY s.timestamp DESC
            LIMIT 10
        """)
        sessions = cursor.fetchall()
        conn.close()

        if sessions:
            df_sessions = pd.DataFrame(sessions, columns=["ID", "Fecha", "Paciente", "Ejercicio"])
            st.dataframe(df_sessions, use_container_width=True)
        else:
            st.info("No hay sesiones registradas aún.")
    except Exception as e:
        st.error(f"⚠️ Error al cargar sesiones recientes: {e}")

    st.divider()

    # ============================================================
    # SECCIÓN DE AYUDA
    # ============================================================
    st.markdown(
        """
        ### ℹ️ Sugerencias de uso
        - **Pacientes:** Registre o seleccione un paciente antes de iniciar una sesión.
        - **Ejercicios:** Defina los movimientos o tests clínicos a analizar.
        - **Sesiones:** Capture o cargue vídeos y registre los resultados automáticamente.
        - **Historial y métricas:** Revise el progreso y genere informes clínicos.
        """
    )

    st.success("✅ Sistema listo para usar. Seleccione una opción en la barra lateral para comenzar.")