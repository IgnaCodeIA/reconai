from db import crud
crud.create_patient("Paciente de prueba", dni="00000000A", age=30, gender="M", notes="Demo")
crud.create_exercise("Flexión de rodilla", "Prueba base de movimiento")