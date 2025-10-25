from core.session_manager import SessionManager

def main():
    # Simulamos una sesión para el paciente y ejercicio 1
    session = SessionManager(
        output_dir="data/exports",
        base_name="simulada",
        patient_id=1,
        exercise_id=1
    )

    session.start_csv(["timestamp", "joint", "angle"])
    session.start_video(640, 480, 30)

    # Simulamos registros de ángulos durante la sesión
    for ang in [90, 100, 110, 120, 115, 95]:
        session.record_angle("rodilla_derecha", ang)
        session.write_csv_row(["sim", "rodilla_derecha", ang])

    session.close_session()

if __name__ == "__main__":
    main()
