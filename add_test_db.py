from db.crud import create_patient, create_exercise
pid = create_patient("Prueba", 30, "M", "Sesión demo")
eid = create_exercise("Flexión de rodilla", "Movimiento base")
print(pid, eid)
