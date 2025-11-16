#Phiteca

#Comienzo
#____________________________________________________________________________________________________________
import mediapipe as mp
import cv2
import numpy as np
import csv
import time
import os


mp_drawing = mp.solutions.drawing_utils
mp_pose = mp.solutions.pose

# Función para calcular el ángulo
def calculate_angle(a, b, c):
    a = np.array(a)
    b = np.array(b)
    c = np.array(c)

    mod_ba = np.sqrt((a[0]-b[0])**2 + (a[1]-b[1])**2)
    mod_bc = np.sqrt((c[0]-b[0])**2 + (c[1]-b[1])**2)
    radians = np.arccos(((a[0] - b[0]) * (c[0] - b[0]) + (a[1] - b[1]) * (c[1] - b[1])) / (mod_ba * mod_bc))
    angle = round(np.abs(radians * 180.0 / np.pi))

    # if angle > 180:
    #     angle = 360 - angle
    return angle

# Fuente origen a analizar, vídeo o webcam ____________________________________________________
# cap = cv2.VideoCapture('Golf v1.mp4')
cap = cv2.VideoCapture(0)

#Con estas funciones se obtiene los FPS y dimensiones del vídeo.
fps= cap.get(cv2.CAP_PROP_FPS)
fps=round(fps)   #lo redondeo por si dan problemas los decimales, con w y h si da problemas
#delay= 1/fps
w= int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
h= int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))


#Grabo el video que vamos a editar
#Tengo que definir primero fourcc, formato del video
#Al final del programa hay que liberarlo, antes del destroyAllWindows, poner un out.release() y antes pongo un out.write(imagen)
fourcc= cv2.VideoWriter_fourcc(*'mp4v')
out = cv2.VideoWriter('output.mp4', fourcc, fps, (w,h))



#defino variable del numero de dato que muestra, la llamo secuencia
secuencia1 = 0

#frecuencia de muestreo de datos para el CSV y pantalla
frec_csv= 0.2

#Ángulo máximo permitido: ___________________________________________________________________
a_max=60
#Ángulo minimo brazo, por ejemplo:
a_min=180

#Creo una variable para resetear el angulo min y max
#a_max_reset=0
a_min_reset=0

#Variable para el cálculo de repeticiones  POR AHORA NO FUNCIONA
rep_mov=0


#Con esto hago un resize para que quede dentro el vídeo _______________________________________
# if w >= 1500 or h>= 800:
#     w_final = int(0.8*w)
#     h_final = int(0.8*h)
# else:
#     w_final = w
#     h_final = h


# cv2.namedWindow("Mediapipe feed", cv2.WINDOW_NORMAL)
# cv2.resizeWindow("Mediapipe feed", w_final, h_final)




with mp_pose.Pose(min_detection_confidence=0.5, min_tracking_confidence=0.5) as pose:
    # Crear archivo CSV para almacenar los datos
    csv_file = open('datos_pose.csv', 'w', newline='')
    csv_writer = csv.writer(csv_file)
    csv_writer.writerow(['Registro (segundos)', 'Secuencia', 
                         'Hombro_X_Der', 'Hombro_Y_Der', 'Codo_X_Der', 'Codo_Y_Der', 'Muñeca_X_Der', 'Muñeca_Y_Der', 'Ángulo brazo Der',
                         'Hombro_X_Izq', 'Hombro_Y_Izq', 'Codo_X_Izq', 'Codo_Y_Izq', 'Muñeca_X_Izq', 'Muñeca_Y_Izq', 'Ángulo brazo Izq',
                         'Cadera_X_Der', 'Cadera_Y_Der', 'Rodilla_X_Der', 'Rodilla_Y_Der', 'Tobillo_X_Der', 'Tobillo_Y_Der', 'Angulo pierna Der', 
                         'Cadera_X_Izq', 'Cadera_Y_Izq', 'Rodilla_X_Izq', 'Rodilla_Y_Izq', 'Tobillo_X_Izq', 'Tobillo_Y_Izq', 'Angulo pierna Izq'])
    #csv_writer.writerow(['Registro (segundos)', 'Secuencia', 'Cadera_X', 'Cadera_Y', 'Rodilla_X', 'Rodilla_Y', 'Tobillo_X', 'Tobillo_Y', 'Angulo'])
    start_time = time.time()
    prev_time = start_time

    while cap.isOpened():
        ret, frame = cap.read()
        # Recolor the image
        image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        image.flags.writeable = False
        # Make the detect.
        results = pose.process(image)
        # Recolor back to BGR
        image.flags.writeable = True
        image = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)

   
        #Poner en blanco el video de fondo   xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
        # cv2.rectangle(image, (0, 0), (w, h), (255, 255, 255), -1)
        
        # Extract landmarks
        try:
            landmarks = results.pose_landmarks.landmark
            
            #Pierna derecha _____
            # Coordenadas cadera, rodiila y tobillo derecho
            hip_x_right = round(landmarks[mp_pose.PoseLandmark.RIGHT_HIP.value].x, 4)
            hip_y_right = round(landmarks[mp_pose.PoseLandmark.RIGHT_HIP.value].y, 4)
            knee_x_right = round(landmarks[mp_pose.PoseLandmark.RIGHT_KNEE.value].x, 4)
            knee_y_right = round(landmarks[mp_pose.PoseLandmark.RIGHT_KNEE.value].y, 4)
            ankle_x_right = round(landmarks[mp_pose.PoseLandmark.RIGHT_ANKLE.value].x, 4)
            ankle_y_right = round(landmarks[mp_pose.PoseLandmark.RIGHT_ANKLE.value].y, 4)
            #Coordenadas pie derec.
            heel_x_right= round(landmarks[mp_pose.PoseLandmark.RIGHT_HEEL.value].x, 4)
            heel_y_right= round(landmarks[mp_pose.PoseLandmark.RIGHT_HEEL.value].y, 4)
            foot_index_x_right= round(landmarks[mp_pose.PoseLandmark.RIGHT_FOOT_INDEX.value].x, 4)
            foot_index_y_right= round(landmarks[mp_pose.PoseLandmark.RIGHT_FOOT_INDEX.value].y, 4)
            # Calcular el ángulo de rodilla derecha
            hip_x_pixel_right = hip_x_right*w
            hip_y_pixel_right = hip_y_right*h
            knee_x_pixel_right = knee_x_right*w
            knee_y_pixel_right = knee_y_right*h
            ankle_x_pixel_right = ankle_x_right*w
            ankle_y_pixel_right = ankle_y_right*h
            angle_knee_right = calculate_angle([hip_x_pixel_right, hip_y_pixel_right], [knee_x_pixel_right, knee_y_pixel_right], [ankle_x_pixel_right, ankle_y_pixel_right])
            
            #Pierna izquierda ______
            # Coordenadas cadera, rodilla y tobillo izquierdo
            hip_x_left = round(landmarks[mp_pose.PoseLandmark.LEFT_HIP.value].x, 4)
            hip_y_left = round(landmarks[mp_pose.PoseLandmark.LEFT_HIP.value].y, 4)
            knee_x_left = round(landmarks[mp_pose.PoseLandmark.LEFT_KNEE.value].x, 4)
            knee_y_left = round(landmarks[mp_pose.PoseLandmark.LEFT_KNEE.value].y, 4)
            ankle_x_left = round(landmarks[mp_pose.PoseLandmark.LEFT_ANKLE.value].x, 4)
            ankle_y_left = round(landmarks[mp_pose.PoseLandmark.LEFT_ANKLE.value].y, 4)
            #Coger coordenadas pie izquierdo.
            heel_x_left= round(landmarks[mp_pose.PoseLandmark.LEFT_HEEL.value].x, 4)
            heel_y_left= round(landmarks[mp_pose.PoseLandmark.LEFT_HEEL.value].y, 4)
            foot_index_x_left= round(landmarks[mp_pose.PoseLandmark.LEFT_FOOT_INDEX.value].x, 4)
            foot_index_y_left= round(landmarks[mp_pose.PoseLandmark.LEFT_FOOT_INDEX.value].y, 4)
            # Calcular el ángulo de cadera, rodilla y tobillo
            hip_x_pixel_left = hip_x_left*w
            hip_y_pixel_left = hip_y_left*h
            knee_x_pixel_left = knee_x_left*w
            knee_y_pixel_left = knee_y_left*h
            ankle_x_pixel_left = ankle_x_left*w
            ankle_y_pixel_left = ankle_y_left*h
            angle_knee_left = calculate_angle([hip_x_pixel_left, hip_y_pixel_left], [knee_x_pixel_left, knee_y_pixel_left], [ankle_x_pixel_left, ankle_y_pixel_left])

            #Brazo derecho ______
            # Coordenadas hombro, codo y muñeca derecho
            shoulder_x_right = round(landmarks[mp_pose.PoseLandmark.RIGHT_SHOULDER.value].x, 4)
            shoulder_y_right = round(landmarks[mp_pose.PoseLandmark.RIGHT_SHOULDER.value].y, 4)
            elbow_x_right = round(landmarks[mp_pose.PoseLandmark.RIGHT_ELBOW.value].x, 4)
            elbow_y_right = round(landmarks[mp_pose.PoseLandmark.RIGHT_ELBOW.value].y, 4)
            wrist_x_right = round(landmarks[mp_pose.PoseLandmark.RIGHT_WRIST.value].x, 4)
            wrist_y_right = round(landmarks[mp_pose.PoseLandmark.RIGHT_WRIST.value].y, 4)
            # Calculatar angulo brazo derecho
            shoulder_x_pixel_right = shoulder_x_right*w
            shoulder_y_pixel_right = shoulder_y_right*h
            elbow_x_pixel_right = elbow_x_right*w
            elbow_y_pixel_right = elbow_y_right*h
            wrist_x_pixel_right = wrist_x_right*w
            wrist_y_pixel_right = wrist_y_right*h
            angle_arm_right = calculate_angle([shoulder_x_pixel_right, shoulder_y_pixel_right], [elbow_x_pixel_right, elbow_y_pixel_right], [wrist_x_pixel_right, wrist_y_pixel_right])

            #Brazo izquierdo _____
            # Coordenadas hombro, codo y muñeca izquierdo
            shoulder_x_left = round(landmarks[mp_pose.PoseLandmark.LEFT_SHOULDER.value].x, 4)
            shoulder_y_left = round(landmarks[mp_pose.PoseLandmark.LEFT_SHOULDER.value].y, 4)
            elbow_x_left = round(landmarks[mp_pose.PoseLandmark.LEFT_ELBOW.value].x, 4)
            elbow_y_left = round(landmarks[mp_pose.PoseLandmark.LEFT_ELBOW.value].y, 4)
            wrist_x_left = round(landmarks[mp_pose.PoseLandmark.LEFT_WRIST.value].x, 4)
            wrist_y_left = round(landmarks[mp_pose.PoseLandmark.LEFT_WRIST.value].y, 4)
            # Calcular angulo izquierdo
            shoulder_x_pixel_left = shoulder_x_left*w
            shoulder_y_pixel_left = shoulder_y_left*h
            elbow_x_pixel_left = elbow_x_left*w
            elbow_y_pixel_left = elbow_y_left*h
            wrist_x_pixel_left = wrist_x_left*w
            wrist_y_pixel_left = wrist_y_left*h
            angle_arm_left = calculate_angle([shoulder_x_pixel_left, shoulder_y_pixel_left], [elbow_x_pixel_left, elbow_y_pixel_left], [wrist_x_pixel_left, wrist_y_pixel_left])

           

            #Esto define varaiables para el texto, hay que revisarlo bien
            font = cv2.FONT_HERSHEY_SIMPLEX
            font_scale = 1
            thickness = 1
            text = 'Angulo brazo derecho: ' + str(angle_arm_right) + " grados"
            text_size = cv2.getTextSize(text, font, font_scale, thickness)[0]
            text_width, text_height = text_size
            padding = 5
            rect_x = 20
            rect_y = 30
            rect_w = text_width + 2 * padding
            rect_h = text_height + 2 * padding

            # Escribe el angulo del brazo derecho
            # cv2.rectangle(image, (rect_x, rect_y), (rect_x +rect_w, rect_y + rect_h), (200, 200, 200), -1)
            # cv2.putText(image, text, (rect_x + padding, rect_y + text_height + padding), font, font_scale, (255, 0, 0), thickness, cv2.LINE_AA)

            #Datos del texto del angulo de la pierna derecha        
            text = 'Angulo pierna derecha: ' + str(angle_knee_right) + " grados"          
            rect_x = 20
            rect_y = 60
            rect_w = text_width + 2 * padding
            rect_h = text_height + 2 * padding

            # Escribe el angulo de la pierna 
            # cv2.rectangle(image, (rect_x, rect_y), (rect_x +rect_w, rect_y + rect_h), (200, 200, 200), -1)
            # cv2.putText(image, text, (rect_x + padding, rect_y + text_height + padding), font, font_scale, (255, 0, 0), thickness, cv2.LINE_AA)
            
            #Escribe los grados del ángulo del brazo derecho en el codo derecho ________________________________________________
            if angle_arm_right >= a_max:
                textoAnguloBrazoDerecho = str(angle_arm_right)
                cv2.putText(image, textoAnguloBrazoDerecho, (round(elbow_x_pixel_right)+20, round(elbow_y_pixel_right)+20), font, font_scale, (0, 255, 0), 2, cv2.LINE_AA)

            if angle_arm_right < a_max:
                textoAnguloBrazoDerecho = str(angle_arm_right)
                cv2.putText(image, textoAnguloBrazoDerecho, (round(elbow_x_pixel_right)+20, round(elbow_y_pixel_right)+20), font, font_scale, (0, 0, 255), 2, cv2.LINE_AA)

            #Escribe los grados del angulo del brazo izquierdo en el coco izquierdo  __________________________________________
            textoAnguloBrazoIzquierdo = str(angle_arm_left)
            cv2.putText(image, textoAnguloBrazoIzquierdo, (round(elbow_x_pixel_left)+20, round(elbow_y_pixel_left)+20), font, font_scale, (0, 255, 0), 2, cv2.LINE_AA)

    
            #Escribe los grados del ángulo de la pierna en la rodilla derecha __________________________________________
            textoAnguloPiernaDerecha = str(angle_knee_right)
            cv2.putText(image, textoAnguloPiernaDerecha, (round(knee_x_pixel_right), round(knee_y_pixel_right)), font, font_scale, (0, 0, 255), 2, cv2.LINE_AA)

            #Escribe los grados del ángulo de la pierna en la rodilla izquierda __________________________________________
            textoAnguloPiernaIzquierda = str(angle_knee_left)
            cv2.putText(image, textoAnguloPiernaIzquierda, (round(knee_x_pixel_left), round(knee_y_pixel_left)), font, font_scale, (0, 0, 255), 2, cv2.LINE_AA)

            #xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
            #Escribe una recta en el hombro derecho _______   __________   ____________    _________    _________    _________    ________    ______
            cv2.rectangle(image, (round(shoulder_x_pixel_right - 200), round(shoulder_y_pixel_right)), (round(shoulder_x_pixel_right + 200), round(shoulder_y_pixel_right+1)), (100, 0, 255), -1)
            #Escribe una recta en el hombro izquierdo _______   __________   ____________    _________    _________    _________    ________    ______
            cv2.rectangle(image, (round(shoulder_x_pixel_left - 200), round(shoulder_y_pixel_left)), (round(shoulder_x_pixel_left + 200), round(shoulder_y_pixel_left+1)), (100, 0, 255), -1)

            #Escribe una recta en la cadera derecha _______   __________   ____________    _________    _________    _________    ________    ______
            cv2.rectangle(image, (round(hip_x_pixel_right - 200), round(hip_y_pixel_right)), (round(hip_x_pixel_right + 200), round(hip_y_pixel_right+1)), (100, 0, 255), -1)
            #Escribe una recta en la cadera izquierda _______   __________   ____________    _________    _________    _________    ________    ______
            cv2.rectangle(image, (round(hip_x_pixel_left - 200), round(hip_y_pixel_left)), (round(hip_x_pixel_left + 200), round(hip_y_pixel_left+1)), (100, 0, 255), -1)

            #Escribe una recta en la rodilla derecho _______   __________   ____________    _________    _________    _________    ________    ______
            # cv2.rectangle(image, (round(knee_x_pixel_right - 200), round(knee_y_pixel_right)), (round(knee_x_pixel_right + 200), round(knee_y_pixel_right+1)), (100, 0, 255), -1)
            # Escribe una recta en la rodilla izquierda _______   __________   ____________    _________    _________    _________    ________    ______
            # cv2.rectangle(image, (round(knee_x_pixel_left - 200), round(knee_y_pixel_left)), (round(knee_x_pixel_left + 200), round(knee_y_pixel_left+1)), (100, 0, 255), -1)

            #Escribe una recta en el tobillo derecho _______   __________   ____________    _________    _________    _________    ________    ______
            # cv2.rectangle(image, (round(ankle_x_pixel_right - 200), round(ankle_y_pixel_right)), (round(ankle_x_pixel_right + 200), round(ankle_y_pixel_right+1)), (100, 0, 255), -1)
            #Escribe una recta en el tobillo izquierdo _______   __________   ____________    _________    _________    _________    ________    ______
            # cv2.rectangle(image, (round(ankle_x_pixel_left - 200), round(ankle_y_pixel_left)), (round(ankle_x_pixel_left + 200), round(ankle_y_pixel_left+1)), (100, 0, 255), -1)
            #xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx


            #Vamos con la columna XD  ___________ ________________   ________________   ______________   _____________   ____________
            #Primero calculo el punto medio de cadera y hombros
            # puntoColumnaHombrosX = int((shoulder_x_pixel_right + shoulder_x_pixel_left)/2)
            # puntoColumnaHombrosY = int((shoulder_y_right + shoulder_y_left)/2)
            
            # puntoColumnaCaderaX = int((hip_x_right + hip_x_left)/2)
            # puntoColumnaCaderaY = int((hip_y_right + hip_y_left)/2)
            # puntoColumnaHombros = (int(((shoulder_x_pixel_right + shoulder_x_pixel_left)/2) * image.shape[1]), int(((shoulder_y_pixel_right + shoulder_y_pixel_left)/2) * image.shape[0]))
            # puntoColumnaCadera = (int(((hip_x_pixel_right + hip_x_pixel_left)/2) * image.shape[1]), int(((hip_y_pixel_right + hip_y_pixel_left)/2) * image.shape[0]))

            puntoColumnaHombros = (int(((shoulder_x_right + shoulder_x_left)/2) * image.shape[1]), int(((shoulder_y_right + shoulder_y_left)/2) * image.shape[0]))
            puntoColumnaCadera = (int(((hip_x_right + hip_x_left)/2) * image.shape[1]), int(((hip_y_right + hip_y_left)/2) * image.shape[0]))
            #Calculo la altura de la columna quiero poner un punto encima del anterior a una distancia determinada _____ ESTO NO FUNCIONA, NI IDEA... :(
            # hColumna_Y = int(((hip_y_right + hip_y_left)/2) - ((shoulder_y_right + shoulder_y_left)/2))
            # puntoColumnaCadera1 = (int(((hip_x_right + hip_x_left)/2) * image.shape[1]), int((((hip_y_right + hip_y_left + 100)/2)) * image.shape[0]))
            
            
            #Ahora los dibujo
            cv2.circle(image, puntoColumnaHombros, 5, (0, 0, 255), -1)
            cv2.circle(image, puntoColumnaCadera, 5, (0, 0, 255), -1)
            # cv2.circle(image, puntoColumnaCadera1, 5, (0, 255, 0), -1)
            #Ahora los uno con una línea
            cv2.line(image, (int(((shoulder_x_right + shoulder_x_left)/2) * image.shape[1]), int(((shoulder_y_right + shoulder_y_left)/2) * image.shape[0])), (int(((hip_x_right + hip_x_left)/2) * image.shape[1]), int(((hip_y_right + hip_y_left)/2) * image.shape[0])), (255, 255, 0), 2)
            #_________________________________________________________________________________________________________

            #Escribe dimensiones del vídeo y fps
            texto3 = 'Dimensiones del video:' + str(w) + '*' + str(h) + ' ->' + str(fps) + 'fps'
            # cv2.putText(image, texto3, (20, 120), font, font_scale, (255, 0, 0), thickness, cv2.LINE_AA)

                        
                        
            # Get current time
            current_time = time.time()
             
            #copia los datos cada frec_csv
            if current_time - prev_time >= frec_csv:
                csv_writer.writerow([int(current_time - start_time), secuencia1, 
                                     round(shoulder_x_pixel_right), round(shoulder_y_pixel_right), round(elbow_x_pixel_right), round(elbow_y_pixel_right), 
                                     round(wrist_x_pixel_right), round(wrist_y_pixel_right), angle_arm_right, 
                                     round(shoulder_x_pixel_left), round(shoulder_y_pixel_left), round(elbow_x_pixel_left), round(elbow_y_pixel_left), 
                                     round(wrist_x_pixel_left), round(wrist_y_pixel_left), angle_arm_left, 
                                     round(hip_x_pixel_right), round(hip_y_pixel_right), round(knee_x_pixel_right), round(knee_y_pixel_right), 
                                     round(ankle_x_pixel_right), round(ankle_y_pixel_right), angle_knee_right, 
                                     round(hip_x_pixel_left), round(hip_y_pixel_left), round(knee_x_pixel_left), round(knee_y_pixel_left), 
                                     round(ankle_x_pixel_left), round(ankle_y_pixel_left), angle_knee_left])
                secuencia1 = secuencia1 +1
                a_min_reset = a_min_reset +1
                #Con esto guardamos el angulo minimo
                if angle_arm_right<a_min:
                    a_min=angle_arm_right
                
                #Con esto contamos el numero de repeticiones FALLOOOOOOOOO, hay que darle una vuelta XD
                #if angle_arm>a_min:
                #    rep_mov=rep_mov+1

                #Con esto Reseteo el angulo minimo
                if a_min_reset>40:
                    a_min_reset=0
                    a_min = 180

                prev_time = current_time

            
            #Rectangulo blanco para texto    XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
            cv2.rectangle(image, (15, 5), (250, 40), (250, 250, 250), -1)


            #Escribe el ángulo máximo objetivo
            #Se escribe en verde si estas por debajo del angulo maximo permitido XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
            if angle_arm_right >= a_max:
                texto4 = 'Angulo max permitido: ' + str(a_max)
                # cv2.putText(image, texto4, (20, 60), font, font_scale, (0, 255, 0), thickness, cv2.LINE_AA)

            #Se pone en rojo si te pasas  XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
            if angle_arm_right < a_max:
                texto4 = 'Angulo max permitido: ' + str(a_max)
                # cv2.putText(image, texto4, (20, 60), font, font_scale, (0, 0, 255), thickness, cv2.LINE_AA)

            

            #Escribe valor mínimo del ángulo brazo
            texto4 = 'Angulo minimo brazo: ' + str(a_min) 
            # cv2.putText(image, texto4, (20, 110), font, font_scale, (255, 0, 0), thickness, cv2.LINE_AA)

            #Escribe el numero de repeticiones
            #texto5 = 'Repeticiones: ' + str(rep_mov) 
            #cv2.putText(image, texto5, (20, 250), font, font_scale, (255, 0, 0), thickness, cv2.LINE_AA)


            
            #con esto mostramos la secuencia del vídeo que estamos estudiando
            texto2 = 'Secuencia:' + str(secuencia1)
            cv2.putText(image, texto2, (20, 30), font, font_scale, (255, 0, 0), thickness, cv2.LINE_AA)



            #ahora dibujamos los puntos y conectores del cuerpo__________
            # Dibuja los conectores de la pierna derecha
            cv2.line(image, (int(hip_x_right * image.shape[1]), int(hip_y_right * image.shape[0])), (int(knee_x_right * image.shape[1]), int(knee_y_right * image.shape[0])), (0, 255, 0), 2)
            cv2.line(image, (int(knee_x_right * image.shape[1]), int(knee_y_right * image.shape[0])), (int(ankle_x_right * image.shape[1]), int(ankle_y_right * image.shape[0])), (0, 255, 0), 2)
            # Dibuja los puntos de la pierna derecha
            hip_point_right = (int(hip_x_right * image.shape[1]), int(hip_y_right * image.shape[0]))
            knee_point_right = (int(knee_x_right * image.shape[1]), int(knee_y_right * image.shape[0]))
            ankle_point_right = (int(ankle_x_right * image.shape[1]),int(ankle_y_right * image.shape[0]))
            cv2.circle(image, hip_point_right, 5, (0, 0, 255), -1)
            cv2.circle(image, knee_point_right, 5, (0, 0, 255), -1)
            cv2.circle(image, ankle_point_right, 5, (0, 0, 255), -1)
            # Dibuja conectores pie der.
            cv2.line(image, (int(ankle_x_right * image.shape[1]), int(ankle_y_right * image.shape[0])), (int(heel_x_right * image.shape[1]), int(heel_y_right * image.shape[0])), (0, 0, 255), 2)
            cv2.line(image, (int(heel_x_right * image.shape[1]), int(heel_y_right * image.shape[0])), (int(foot_index_x_right * image.shape[1]), int(foot_index_y_right * image.shape[0])), (0, 0, 255), 2)
            cv2.line(image, (int(foot_index_x_right * image.shape[1]), int(foot_index_y_right * image.shape[0])), (int(ankle_x_right * image.shape[1]), int(ankle_y_right * image.shape[0])), (0, 0, 255), 2)
             # Dibuja puntos pie der.
            heel_point_right = (int(heel_x_right * image.shape[1]), int(heel_y_right * image.shape[0]))
            foot_index_point_right = (int(foot_index_x_right * image.shape[1]), int(foot_index_y_right * image.shape[0]))
            cv2.circle(image, heel_point_right, 5, (0, 0, 255), -1)
            cv2.circle(image, foot_index_point_right, 5, (0, 0, 255), -1)
            #___________________________________________________
            # Dibuja los conectores de la pierna izquierda
            cv2.line(image, (int(hip_x_left * image.shape[1]), int(hip_y_left * image.shape[0])), (int(knee_x_left * image.shape[1]), int(knee_y_left * image.shape[0])), (0, 255, 0), 2)
            cv2.line(image, (int(knee_x_left * image.shape[1]), int(knee_y_left * image.shape[0])), (int(ankle_x_left * image.shape[1]), int(ankle_y_left * image.shape[0])), (0, 255, 0), 2)
            # Dibuja los puntos de la pierna izquierda
            hip_point_left = (int(hip_x_left * image.shape[1]), int(hip_y_left * image.shape[0]))
            knee_point_left = (int(knee_x_left * image.shape[1]), int(knee_y_left * image.shape[0]))
            ankle_point_left = (int(ankle_x_left * image.shape[1]),int(ankle_y_left * image.shape[0]))
            cv2.circle(image, hip_point_left, 5, (0, 0, 255), -1)
            cv2.circle(image, knee_point_left, 5, (0, 0, 255), -1)
            cv2.circle(image, ankle_point_left, 5, (0, 0, 255), -1)
            # Dibuja concetores del pie izquierdo.
            cv2.line(image, (int(ankle_x_left * image.shape[1]), int(ankle_y_left * image.shape[0])), (int(heel_x_left * image.shape[1]), int(heel_y_left * image.shape[0])), (0, 0, 255), 2)
            cv2.line(image, (int(heel_x_left * image.shape[1]), int(heel_y_left * image.shape[0])), (int(foot_index_x_left * image.shape[1]), int(foot_index_y_left * image.shape[0])), (0, 0, 255), 2)
            cv2.line(image, (int(foot_index_x_left * image.shape[1]), int(foot_index_y_left * image.shape[0])), (int(ankle_x_left * image.shape[1]), int(ankle_y_left * image.shape[0])), (0, 0, 255), 2)
             # Dibuja puntos pie izquierdo.
            heel_point_left = (int(heel_x_left * image.shape[1]), int(heel_y_left * image.shape[0]))
            foot_index_point_left = (int(foot_index_x_left * image.shape[1]), int(foot_index_y_left * image.shape[0]))
            cv2.circle(image, heel_point_left, 5, (0, 0, 255), -1)
            cv2.circle(image, foot_index_point_left, 5, (0, 0, 255), -1)
            #__________________________________________________
            # Dibuja los conectores del brazo derecho
            cv2.line(image, (int(shoulder_x_right * image.shape[1]), int(shoulder_y_right * image.shape[0])), (int(elbow_x_right * image.shape[1]), int(elbow_y_right * image.shape[0])), (0, 255, 0), 2)
            cv2.line(image, (int(elbow_x_right * image.shape[1]), int(elbow_y_right * image.shape[0])), (int(wrist_x_right * image.shape[1]), int(wrist_y_right * image.shape[0])), (0, 255, 0), 2)
            #Dibuja los puntos del brazo derecho
            shoulder_point = (int(shoulder_x_right * image.shape[1]), int(shoulder_y_right * image.shape[0]))
            elbow_point = (int(elbow_x_right * image.shape[1]), int(elbow_y_right * image.shape[0]))
            wrist_point = (int(wrist_x_right * image.shape[1]), int(wrist_y_right * image.shape[0]))
            cv2.circle(image, shoulder_point, 5, (0, 0, 255), -1)
            cv2.circle(image, elbow_point, 5, (0, 0, 255), -1)
            cv2.circle(image, wrist_point, 5, (0, 0, 255), -1)
            #________________________________________________
            # Dibuja los conectores del brazo izquierdo
            cv2.line(image, (int(shoulder_x_left * image.shape[1]), int(shoulder_y_left * image.shape[0])), (int(elbow_x_left * image.shape[1]), int(elbow_y_left * image.shape[0])), (0, 255, 0), 2)
            cv2.line(image, (int(elbow_x_left * image.shape[1]), int(elbow_y_left * image.shape[0])), (int(wrist_x_left * image.shape[1]), int(wrist_y_left * image.shape[0])), (0, 255, 0), 2)
             # Dibuja los puntos del brazo izquierdo
            shoulder_point_left = (int(shoulder_x_left * image.shape[1]), int(shoulder_y_left * image.shape[0]))
            elbow_point_left = (int(elbow_x_left * image.shape[1]), int(elbow_y_left * image.shape[0]))
            wrist_point_left = (int(wrist_x_left * image.shape[1]), int(wrist_y_left * image.shape[0]))
            cv2.circle(image, shoulder_point_left, 5, (0, 0, 255), -1)
            cv2.circle(image, elbow_point_left, 5, (0, 0, 255), -1)
            cv2.circle(image, wrist_point_left, 5, (0, 0, 255), -1)
            #__________________________________________________________________
            #Dibujar conectores de torso
            cv2.line(image, (int(shoulder_x_right * image.shape[1]), int(shoulder_y_right * image.shape[0])), (int(shoulder_x_left * image.shape[1]), int(shoulder_y_left * image.shape[0])), (0, 255, 255), 2)
            cv2.line(image, (int(shoulder_x_left * image.shape[1]), int(shoulder_y_left * image.shape[0])), (int(hip_x_left * image.shape[1]), int(hip_y_left * image.shape[0])), (0, 255, 255), 2)
            cv2.line(image, (int(hip_x_left * image.shape[1]), int(hip_y_left * image.shape[0])), (int(hip_x_right * image.shape[1]), int(hip_y_right * image.shape[0])), (0, 255, 255), 2)
            cv2.line(image, (int(hip_x_right * image.shape[1]), int(hip_y_right * image.shape[0])), (int(shoulder_x_right * image.shape[1]), int(shoulder_y_right * image.shape[0])), (0, 255, 255), 2)
            #__________________________________________________________________




        except:
            pass

        cv2.imshow('Mediapipe feed', image)
        if cv2.waitKey(10) & 0xFF == ord('q'):
            break
        out.write(image)  #aquí grabamos el video con los datos de 'image'

    csv_file.close()
    cap.release()
    out.release()   #aqui liberamos el video
    #Cambiamos el nombre del archivo CSV y mp4, le pongo dimension, fps y tiempo
    #redondeo el tiempo
    hora_archivo = round(current_time)
    archivo = "datos_pose.csv"
    nombre_nuevo = str(w) + "x" + str(h) + "-" + str(fps) + "-" + str(hora_archivo) + ".csv"
    os.rename(archivo, nombre_nuevo)
    #Cambio el nombre del mp4 y le pongo el mismo que el csv
    archivo = "output.mp4"
    nombre_nuevo = str(w) + "x" + str(h) + "-" + str(fps) + "-" + str(hora_archivo) + ".mp4"
    os.rename(archivo, nombre_nuevo)

    cv2.destroyAllWindows()
