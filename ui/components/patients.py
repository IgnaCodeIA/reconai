import streamlit as st
from db import crud


def app():
    """
    Interfaz Streamlit para la gestión de pacientes.
    Permite crear, editar, eliminar y listar pacientes registrados.
    """
    st.title("👩‍⚕️ Gestión de Pacientes")
    st.write("Agregue, edite o elimine registros de pacientes de la clínica.")

    # ============================================================
    # FORMULARIO DE ALTA DE PACIENTE
    # ============================================================
    with st.form("add_patient_form"):
        st.subheader("➕ Añadir nuevo paciente")
        name = st.text_input("Nombre completo")
        dni = st.text_input("DNI")
        age = st.number_input("Edad", min_value=0, max_value=120, step=1)
        gender = st.selectbox("Género", ["M", "F", "Other"])
        notes = st.text_area("Notas o diagnóstico clínico")

        submitted = st.form_submit_button("Guardar paciente")

        if submitted:
            if not name.strip() or not dni.strip():
                st.error("El nombre y el DNI son obligatorios.")
            else:
                try:
                    crud.create_patient(name, dni, age, gender, notes)
                    st.success(f"Paciente '{name}' registrado correctamente.")
                    st.rerun()
                except Exception as e:
                    st.error(f"Error al registrar el paciente: {e}")

    st.divider()

    # ============================================================
    # LISTADO DE PACIENTES EXISTENTES
    # ============================================================
    st.subheader("📋 Pacientes registrados")

    try:
        patients = crud.get_all_patients()
    except Exception as e:
        st.error(f"Error al obtener pacientes: {e}")
        return

    if not patients:
        st.info("Aún no hay pacientes registrados.")
        return

    # Encabezado de tabla
    st.markdown(
        "| Nombre | DNI | Edad | Género | Notas | Acciones |  |"
        "\n|:--|:--|:--|:--|:--|:--|:--|"
    )

    for patient in patients:
        patient_id, name, dni, age, gender, notes, created_at = patient

        cols = st.columns([2, 2, 1, 1, 3, 1, 1])
        cols[0].text(name)
        cols[1].text(dni)
        cols[2].text(str(age or ""))
        cols[3].text(gender or "")
        cols[4].text(notes or "")

        edit_btn = cols[5].button("✏️ Editar", key=f"edit_{patient_id}")
        del_btn = cols[6].button("🗑️ Eliminar", key=f"delete_{patient_id}")

        # ============================================================
        # INICIO DE EDICIÓN
        # ============================================================
        if edit_btn:
            st.session_state["editing_patient_id"] = patient_id

        # Mostrar formulario si este paciente está en edición
        if st.session_state.get("editing_patient_id") == patient_id:
            with st.form(f"edit_form_{patient_id}", clear_on_submit=False):
                st.subheader(f"Editar paciente ID {patient_id}")

                new_name = st.text_input("Nombre completo", value=name, key=f"name_{patient_id}")
                new_dni = st.text_input("DNI", value=dni, key=f"dni_{patient_id}")
                new_age = st.number_input("Edad", min_value=0, max_value=120, step=1, value=age or 0, key=f"age_{patient_id}")
                gender_index = ["M", "F", "Other"].index(gender) if gender in ["M", "F", "Other"] else 0
                new_gender = st.selectbox("Género", ["M", "F", "Other"], index=gender_index, key=f"gender_{patient_id}")
                new_notes = st.text_area("Notas o diagnóstico clínico", value=notes or "", key=f"notes_{patient_id}")

                update = st.form_submit_button("Actualizar")
                cancel = st.form_submit_button("Cancelar")

                if update:
                    if not new_name.strip() or not new_dni.strip():
                        st.error("El nombre y el DNI son obligatorios.")
                    else:
                        try:
                            updated = crud.update_patient(patient_id, new_name, new_dni, new_age, new_gender, new_notes)
                            if updated:
                                st.success(f"Paciente '{new_name}' actualizado correctamente.")
                            else:
                                st.warning("No se detectaron cambios.")
                            st.session_state.pop("editing_patient_id", None)
                            st.rerun()
                        except Exception as e:
                            st.error(f"Error al actualizar paciente: {e}")

                elif cancel:
                    st.session_state.pop("editing_patient_id", None)
                    st.info("Edición cancelada.")
                    st.rerun()

        # ============================================================
        # ELIMINACIÓN DE PACIENTE (con session_state)
        # ============================================================
        if del_btn:
            st.session_state["delete_candidate"] = patient_id

        if st.session_state.get("delete_candidate") == patient_id:
            st.warning(f"¿Seguro que desea eliminar al paciente '{name}' y todas sus sesiones asociadas?")
            confirm = st.button("Confirmar eliminación", key=f"confirm_delete_{patient_id}")
            cancel = st.button("Cancelar", key=f"cancel_delete_{patient_id}")

            if confirm:
                try:
                    deleted = crud.delete_patient(patient_id)
                    if deleted:
                        st.success(f"Paciente '{name}' eliminado correctamente.")
                    else:
                        st.warning("No se encontró el registro a eliminar.")
                    st.session_state.pop("delete_candidate", None)
                    st.rerun()
                except Exception as e:
                    st.error(f"Error al eliminar paciente: {e}")

            elif cancel:
                st.session_state.pop("delete_candidate", None)
                st.info("Eliminación cancelada.")
                st.rerun()