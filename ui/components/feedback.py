# ui/components/feedback.py
"""
Módulo de feedback para usuarios clínicos.
Permite reportar problemas, sugerencias y comentarios sobre el sistema.
"""

import streamlit as st
from db import feedback_crud


# ============================================================
# OPCIONES DEL FORMULARIO
# ============================================================

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
    "🐛 Problema o error",
    "💡 Sugerencia de mejora",
    "⚡ Lentitud del sistema",
    "📱 Difícil de usar",
    "✨ Nueva funcionalidad",
    "👍 Comentario positivo"
]


# ============================================================
# UTILIDADES
# ============================================================

def _get_user_agent():
    """Obtiene información del navegador (si está disponible)."""
    try:
        return "Streamlit Web App"
    except:
        return None


def _get_screen_resolution():
    """Obtiene resolución de pantalla (si está disponible)."""
    try:
        return "Unknown"
    except:
        return None


def _init_state():
    """Inicializa estados de Streamlit."""
    st.session_state.setdefault("feedback_submitted", False)
    st.session_state.setdefault("last_feedback_id", None)


# ============================================================
# APP PRINCIPAL
# ============================================================

def app():
    _init_state()
    
    st.title("💬 Feedback del Sistema")
    st.write("Ayúdanos a mejorar Recon IA compartiendo tu experiencia, reportando problemas o sugiriendo mejoras.")
    
    # ============================================================
    # CONFIRMACIÓN DE ENVÍO
    # ============================================================
    
    if st.session_state.get("feedback_submitted", False):
        feedback_id = st.session_state.get("last_feedback_id")
        
        st.success(f"✅ ¡Gracias por tu feedback! Tu reporte ha sido registrado con ID #{feedback_id}")
        st.info("Tu comentario nos ayuda a mejorar el sistema.")
        
        if st.button("📝 Enviar otro feedback", type="primary"):
            st.session_state["feedback_submitted"] = False
            st.session_state["last_feedback_id"] = None
            st.rerun()
        
        return
    
    # ============================================================
    # FORMULARIO DE FEEDBACK
    # ============================================================
    
    st.subheader("📝 Nuevo feedback")
    
    with st.form("feedback_form", clear_on_submit=True):
        # Componente
        component = st.selectbox(
            "¿Qué parte del sistema te gustaría comentar? *",
            COMPONENTS,
            help="Selecciona el componente relacionado con tu feedback"
        )
        
        # Tipo de feedback
        feedback_type = st.selectbox(
            "Tipo de feedback *",
            FEEDBACK_TYPES,
            help="Indica qué tipo de comentario quieres compartir"
        )
        
        # Título
        title = st.text_input(
            "Título breve *",
            max_chars=100,
            placeholder="Ej: Error al guardar sesión de vídeo",
            help="Resumen corto del problema o sugerencia (máximo 100 caracteres)"
        )
        
        # Descripción
        description = st.text_area(
            "Descripción detallada *",
            max_chars=500,
            height=150,
            placeholder="Describe el problema con el mayor detalle posible:\n"
                       "• ¿Qué estabas intentando hacer?\n"
                       "• ¿Qué pasó?\n"
                       "• ¿Qué esperabas que pasara?\n"
                       "• ¿Cómo podemos reproducir el problema?",
            help="Proporciona todos los detalles relevantes (máximo 500 caracteres)"
        )
        
        # Contador de caracteres
        st.caption(f"Caracteres usados: {len(description)}/500")
        
        # Botón de envío
        st.markdown("---")
        submit = st.form_submit_button("📤 Enviar feedback", type="primary", use_container_width=True)
        
        if submit:
            # Validaciones
            errors = []
            
            if not component:
                errors.append("Debes seleccionar un componente")
            
            if not feedback_type:
                errors.append("Debes seleccionar un tipo de feedback")
            
            if not title or len(title.strip()) < 5:
                errors.append("El título debe tener al menos 5 caracteres")
            
            if not description or len(description.strip()) < 10:
                errors.append("La descripción debe tener al menos 10 caracteres")
            
            # Mostrar errores
            if errors:
                for error in errors:
                    st.error(f"⚠️ {error}")
            else:
                # Guardar feedback
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
                    st.error(f"❌ Error al guardar el feedback: {e}")
    
    # ============================================================
    # INFORMACIÓN ADICIONAL
    # ============================================================
    
    st.divider()
    
    with st.expander("ℹ️ Consejos para un buen feedback"):
        st.markdown("""
        **Para reportar un problema:**
        - Describe los pasos exactos que seguiste
        - Indica qué esperabas que ocurriera
        - Explica qué ocurrió en su lugar
        - Si es posible, indica cuándo empezó a ocurrir
        
        **Para sugerir una mejora:**
        - Explica qué te gustaría que se añadiera o cambiara
        - Describe cómo te ayudaría en tu trabajo
        - Si tienes ideas de cómo implementarlo, compártelas
        
        **Ejemplos de buen feedback:**
        - ✅ "Al pausar la grabación, el contador de secuencia se reinicia en lugar de mantener el valor"
        - ✅ "Sería útil poder exportar las métricas a Excel para compartir con el equipo médico"
        - ❌ "No funciona" (demasiado vago)
        - ❌ "El sistema es lento" (falta especificar dónde y cuándo)
        """)
    
    with st.expander("🔒 Privacidad"):
        st.markdown("""
        Tu feedback se almacena de forma local en este sistema y solo será visto por el equipo de desarrollo.
        
        **Información que recopilamos:**
        - Componente y tipo de feedback
        - Título y descripción que proporciones
        - Fecha y hora de envío
        - Información técnica básica (navegador, resolución de pantalla)
        
        **No recopilamos:**
        - Datos personales identificables
        - Información de pacientes
        - Contenido de sesiones o vídeos
        """)