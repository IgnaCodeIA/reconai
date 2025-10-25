from db import crud

def main():
    print("\n=== PACIENTES ===")
    patients = crud.get_all_patients()
    for p in patients:
        print(p)

    print("\n=== EJERCICIOS ===")
    exercises = crud.get_all_exercises()
    for e in exercises:
        print(e)

    print("\n=== SESIONES ===")
    if patients:
        patient_id = patients[0][0]
        sessions = crud.get_sessions_by_patient(patient_id)
        for s in sessions:
            print(s)

            # Para cada sesión, mostramos las métricas
            session_id = s[0]
            print(f"\n  → Métricas de sesión {session_id}:")
            metrics = crud.get_metrics_by_session(session_id)
            for m in metrics:
                print("    ", m)

    print("\n=== RESUMEN GENERAL ===")
    print(crud.get_table_counts())

if __name__ == "__main__":
    main()
