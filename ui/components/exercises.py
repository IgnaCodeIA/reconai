import streamlit as st
from db import crud


def app():
    """
    Interfaz Streamlit para la gestión de ejercicios.
    Permite registrar, visualizar, editar y eliminar ejercicios disponibles.
    """
    st.title("🏋️ Gestión de Ejercicios")
    st.write("Cree, edite o elimine ejercicios utilizados en las sesiones de análisis.")

    # ------------------------------------------------------------
    # FORMULARIO: NUEVO EJERCICIO
    # ------------------------------------------------------------
    with st.form("add_exercise_form"):
        st.subheader("➕ Añadir nuevo ejercicio")
        name = st.text_input("Nombre del ejercicio")
        description = st.text_area("Descripción o notas")
        submitted = st.form_submit_button("Guardar ejercicio")

        if submitted:
            if not name.strip():
                st.error("⚠️ El nombre del ejercicio es obligatorio.")
            else:
                try:
                    crud.create_exercise(name.strip(), description.strip() or None)
                    st.success(f"✅ Ejercicio '{name.strip()}' registrado correctamente.")
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ Error al registrar el ejercicio: {e}")

    st.divider()

    # ------------------------------------------------------------
    # LISTADO + FILTRO
    # ------------------------------------------------------------
    st.subheader("📋 Ejercicios registrados")

    try:
        exercises = crud.get_all_exercises()
    except Exception as e:
        st.error(f"⚠️ Error al obtener ejercicios: {e}")
        return

    if not exercises:
        st.info("Aún no hay ejercicios registrados.")
        return

    # Filtro rápido por nombre/descr.
    q = st.text_input("🔎 Buscar", placeholder="Filtre por nombre o descripción...")
    if q:
        q_lower = q.lower()
        exercises = [
            ex for ex in exercises
            if (ex[1] and q_lower in ex[1].lower()) or (ex[2] and q_lower in (ex[2] or "").lower())
        ]

    if not exercises:
        st.info("No hay resultados para el filtro actual.")
        return

    # Cabecera de columnas
    head = st.columns([3, 6, 1, 1])
    head[0].markdown("**Nombre**")
    head[1].markdown("**Descripción**")
    head[2].markdown("**Editar**")
    head[3].markdown("**Eliminar**")

    # Estado local para edición/eliminación
    st.session_state.setdefault("editing_exercise_id", None)
    st.session_state.setdefault("delete_candidate", None)

    # Tabla simple con acciones por fila
    for exercise in exercises:
        exercise_id, exercise_name, exercise_desc = exercise

        cols = st.columns([3, 6, 1, 1])
        cols[0].write(exercise_name or "—")
        cols[1].write(exercise_desc or "—")
        edit_btn = cols[2].button("✏️", key=f"edit_{exercise_id}")
        del_btn = cols[3].button("🗑️", key=f"delete_{exercise_id}")

        # ---------- INICIO DE EDICIÓN ----------
        if edit_btn:
            st.session_state["editing_exercise_id"] = exercise_id

        if st.session_state.get("editing_exercise_id") == exercise_id:
            with st.form(f"edit_form_{exercise_id}", clear_on_submit=False):
                st.subheader(f"Editar ejercicio ID {exercise_id}")

                new_name = st.text_input(
                    "Nombre del ejercicio",
                    value=exercise_name or "",
                    key=f"name_{exercise_id}",
                )
                new_desc = st.text_area(
                    "Descripción o notas",
                    value=exercise_desc or "",
                    key=f"desc_{exercise_id}",
                )

                c_upd, c_cancel = st.columns(2)
                update = c_upd.form_submit_button("Actualizar")
                cancel = c_cancel.form_submit_button("Cancelar")

                if update:
                    if not new_name.strip():
                        st.error("⚠️ El nombre del ejercicio es obligatorio.")
                    else:
                        try:
                            updated = crud.update_exercise(exercise_id, new_name.strip(), (new_desc or "").strip() or None)
                            if updated:
                                st.success(f"✅ Ejercicio '{new_name.strip()}' actualizado correctamente.")
                            else:
                                st.info("No se detectaron cambios.")
                            st.session_state.pop("editing_exercise_id", None)
                            st.rerun()
                        except Exception as e:
                            st.error(f"❌ Error al actualizar el ejercicio: {e}")

                elif cancel:
                    st.session_state.pop("editing_exercise_id", None)
                    st.info("❎ Edición cancelada.")
                    st.rerun()

        # ---------- ELIMINACIÓN (confirmación) ----------
        if del_btn:
            st.session_state["delete_candidate"] = exercise_id

        if st.session_state.get("delete_candidate") == exercise_id:
            st.warning(f"⚠️ ¿Seguro que desea eliminar el ejercicio '{exercise_name}' y sus sesiones asociadas?")
            c1, c2 = st.columns(2)
            confirm = c1.button("Confirmar eliminación", key=f"confirm_delete_{exercise_id}")
            cancel = c2.button("Cancelar", key=f"cancel_delete_{exercise_id}")

            if confirm:
                try:
                    deleted = crud.delete_exercise(exercise_id)
                    if deleted:
                        st.success(f"🗑️ Ejercicio '{exercise_name}' eliminado correctamente.")
                    else:
                        st.warning("No se encontró el registro a eliminar.")
                    st.session_state.pop("delete_candidate", None)
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ Error al eliminar ejercicio: {e}")

            elif cancel:
                st.session_state.pop("delete_candidate", None)
                st.info("❎ Eliminación cancelada.")
                st.rerun() 