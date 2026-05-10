from __future__ import annotations

import streamlit as st

from db import crud
from ai.orchestrator import stream
from core.logger import get_logger

log = get_logger("ui.assistant")


def _init_state() -> None:
    st.session_state.setdefault("ai_history", [])
    st.session_state.setdefault("ai_context_patient", None)


def _reset_chat() -> None:
    st.session_state["ai_history"] = []
    st.session_state["ai_context_patient"] = None


def _render_history(history: list[dict]) -> None:
    for msg in history:
        role = msg.get("role")
        content = msg.get("content", "")

        if role == "user":
            with st.chat_message("user"):
                st.markdown(content)
        elif role == "assistant" and content:
            with st.chat_message("assistant"):
                st.markdown(content)


def _build_context_prefix(patient_name: str | None) -> str:
    if not patient_name:
        return ""
    return f"[Contexto: el paciente actual es '{patient_name}'.]\n\n"


def app() -> None:
    """Render the AI assistant chat page (history, patient-context selector, streaming response)."""
    _init_state()

    st.title("Asistente IA")
    st.write("Consulta datos de pacientes, evolución de métricas y resúmenes de sesiones.")

    with st.sidebar:
        st.markdown("---")
        st.markdown("### Asistente IA")

        try:
            patients = crud.get_all_patients()
        except Exception as exc:
            log.error("Error loading patients: %s", exc)
            patients = []

        patient_options = ["Ninguno (general)"] + [p[1] for p in patients]
        current_context = st.session_state.get("ai_context_patient") or "Ninguno (general)"

        selected = st.selectbox(
            "Paciente en contexto",
            patient_options,
            index=patient_options.index(current_context) if current_context in patient_options else 0,
            help="Selecciona un paciente para que el asistente lo tenga en cuenta desde el inicio.",
            key="ai_patient_selector",
        )

        new_context = selected if selected != "Ninguno (general)" else None
        if new_context != st.session_state.get("ai_context_patient"):
            log.debug("AI context patient changed to %s", new_context)
            st.session_state["ai_context_patient"] = new_context

        if st.button("Limpiar conversación", use_container_width=True):
            _reset_chat()
            st.rerun()

    history: list[dict] = st.session_state["ai_history"]

    if not history:
        with st.chat_message("assistant"):
            patient_ctx = st.session_state.get("ai_context_patient")
            if patient_ctx:
                st.markdown(
                    f"Hola. Estoy listo para ayudarte con los datos de **{patient_ctx}**. "
                    "¿Qué quieres consultar?"
                )
            else:
                st.markdown(
                    "Hola. Soy el asistente clínico de Recon IA. "
                    "Puedo ayudarte a consultar sesiones, analizar la evolución de métricas "
                    "y generar resúmenes de pacientes. ¿Sobre qué paciente o sesión quieres saber?"
                )
    else:
        _render_history(history)

    user_input = st.chat_input("Escribe tu pregunta...")

    if not user_input:
        return

    with st.chat_message("user"):
        st.markdown(user_input)

    patient_ctx = st.session_state.get("ai_context_patient")
    if patient_ctx and not history:
        effective_input = _build_context_prefix(patient_ctx) + user_input
    else:
        effective_input = user_input

    with st.chat_message("assistant"):
        placeholder = st.empty()
        full_response = ""

        try:
            for chunk in stream(effective_input, history):
                full_response += chunk
                placeholder.markdown(full_response + "▌")

            placeholder.markdown(full_response)

        except ValueError as exc:
            placeholder.error(str(exc))
            log.error("Configuration error: %s", exc)

        except Exception as exc:
            placeholder.error(
                f"Error al conectar con el asistente: {exc}. "
                "Revisa la consola para más detalles."
            )
            log.exception("Unexpected error in the assistant")

    st.rerun()
