from db import crud

# Crear un paciente de prueba
print("Creando paciente...")
pid = crud.create_patient("Paciente Test", "12345678A", 30, "M", "Notas de prueba")
print(f"✅ Paciente creado con ID {pid}")

# Verificar que aparece en la base de datos
print("\nListando pacientes:")
patients = crud.get_all_patients()
for p in patients:
    print(p)

# Actualizar el paciente
print("\nActualizando paciente...")
res_update = crud.update_patient(pid, name="Paciente Modificado", age=31)
print(f"Resultado update: {res_update}")

# Comprobar si se actualizó
p2 = crud.get_patient_by_id(pid)
print(f"Después del update: {p2}")

# Eliminar el paciente
print("\nEliminando paciente...")
res_delete = crud.delete_patient(pid)
print(f"Resultado delete: {res_delete}")

# Verificar que ya no está
patients = crud.get_all_patients()
print("\nPacientes restantes:")
for p in patients:
    print(p)