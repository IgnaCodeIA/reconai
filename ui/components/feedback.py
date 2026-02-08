import streamlit as st
from db import feedback_crud


COMPONENTS = [
    "Inicio / Dashboard",
    "Pacientes",
    "Ejercicios",
    "Sesiones - Captura de video",
    "Sesiones - Subir vídeo",
    "Historial y Métricas",
    "Informes PDF",
    "Sistema general"
]

FEEDBACK_TYPES = [
    "Problema o error",
    "Sugerencia de mejora",
    "Lentitud del sistema",
    "Difícil de usar",
    "Nueva funcionalidad",
    "Comentario positivo"
]


def _get_user_agent():
    try:
        return "Streamlit Web App"
    except:
        return None


def _get_screen_resolution():
    try:
        return "Unknown"
    except:
        return None


def _init_state():
    st.session_state.setdefault("feedback_submitted", False)
    st.session_state.setdefault("last_feedback_id", None)


def app():
    _init_state()
    
    st.title("Feedback del Sistema")
    st.write("Ayúdanos a mejorar Recon IA compartiendo tu experiencia, reportando problemas o sugiriendo mejoras.")
    
    if st.session_state.get("feedback_submitted", False):
        feedback_id = st.session_state.get("last_feedback_id")
        
        st.success(f"Gracias por tu feedback. Tu reporte ha sido registrado con ID #{feedback_id}")
        st.info("Tu comentario nos ayuda a mejorar el sistema.")
        
        if st.button("Enviar otro feedback", type="primary"):
            st.session_state["feedback_submitted"] = False
            st.session_state["last_feedback_id"] = None
            st.rerun()
        
        return
    
    st.subheader("Nuevo feedback")
    
    with st.form("feedback_form", clear_on_submit=True):
        component = st.selectbox(
            "¿Qué parte del sistema te gustaría comentar?",
            COMPONENTS,
            help="Selecciona el componente relacionado con tu feedback"
        )
        
        feedback_type = st.selectbox(
            "Tipo de feedback",
            FEEDBACK_TYPES,
            help="Indica qué tipo de comentario quieres compartir"
        )
        
        title = st.text_input(
            "Título breve",
            max_chars=100,
            placeholder="Ej: Error al guardar sesión de vídeo",
            help="Resumen corto del problema o sugerencia (máximo 100 caracteres)"
        )
        
        description = st.text_area(
            "Descripción detallada",
            max_chars=500,
            height=150,
            placeholder="Describe el problema con el mayor detalle posible",
            help="Proporciona todos los detalles relevantes (máximo 500 caracteres)"
        )
        
        st.caption(f"Caracteres usados: {len(description)}/500")
        
        st.markdown("---")
        submit = st.form_submit_button("Enviar feedback", type="primary", use_container_width=True)
        
        if submit:
            errors = []
            
            if not component:
                errors.append("Debes seleccionar un componente")
            
            if not feedback_type:
                errors.append("Debes seleccionar un tipo de feedback")
            
            if not title or len(title.strip()) < 5:
                errors.append("El título debe tener al menos 5 caracteres")
            
            if not description or len(description.strip()) < 10:
                errors.append("La descripción debe tener al menos 10 caracteres")
            
            if errors:
                for error in errors:
                    st.error(error)
            else:
                try:
                    user_agent = _get_user_agent()
                    screen_resolution = _get_screen_resolution()
                    
                    feedback_id = feedback_crud.create_feedback(
                        component=component,
                        feedback_type=feedback_type,
                        title=title.strip(),
                        description=description.strip(),
                        user_agent=user_agent,
                        screen_resolution=screen_resolution
                    )
                    
                    st.session_state["feedback_submitted"] = True
                    st.session_state["last_feedback_id"] = feedback_id
                    st.rerun()
                
                except Exception as e:
                    st.error(f"Error al guardar el feedback: {e}")
    
    st.divider()
    
    with st.expander("Consejos para un buen feedback"):
        st.markdown("""
        **Para reportar un problema:**
        - Describe los pasos exactos que seguiste
        - Indica qué esperabas que ocurriera
        - Explica qué ocurrió en su lugar
        
        **Para sugerir una mejora:**
        - Explica qué te gustaría que se añadiera o cambiara
        - Describe cómo te ayudaría en tu trabajo
        """)
    
    with st.expander("Privacidad"):
        st.markdown("""
        Tu feedback se almacena de forma local en este sistema.
        
        **Información que recopilamos:**
        - Componente y tipo de feedback
        - Título y descripción
        - Fecha y hora de envío
        
        **No recopilamos:**
        - Datos personales identificables
        - Información de pacientes
        """)