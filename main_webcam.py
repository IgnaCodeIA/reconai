import cv2
import time
from core.pose_detection import PoseDetector
from core.angle_calculator import calculate_angle
from core.video_capture import VideoCaptureManager
from core.session_manager import SessionManager
from core.utils import log_info, log_error


def main():
    log_info("Iniciando captura en vivo con webcam...")

    # Inicialización de módulos
    detector = PoseDetector()
    video = VideoCaptureManager(0)  # Webcam local
    session = SessionManager(
        output_dir="data/exports",
        base_name="captura_demo",
        patient_id=1,          # <-- asigna aquí un ID existente en la BD
        exercise_id=1          # <-- idem
    )

    session.start_session(video.width, video.height, video.fps)

    while True:
        ret, frame = video.read_frame()
        if not ret:
            log_error("No se pudo leer el frame de la cámara.")
            break

        image, results = detector.process_frame(frame)
        if results and results.pose_landmarks:
            lm = detector.extract_landmarks(results)

            try:
                # =============================
                # Cálculo de ángulos articulares
                # =============================
                shoulder_r = (lm["RIGHT_SHOULDER"][0] * video.width, lm["RIGHT_SHOULDER"][1] * video.height)
                elbow_r = (lm["RIGHT_ELBOW"][0] * video.width, lm["RIGHT_ELBOW"][1] * video.height)
                wrist_r = (lm["RIGHT_WRIST"][0] * video.width, lm["RIGHT_WRIST"][1] * video.height)
                angle_arm_r = calculate_angle(shoulder_r, elbow_r, wrist_r)

                shoulder_l = (lm["LEFT_SHOULDER"][0] * video.width, lm["LEFT_SHOULDER"][1] * video.height)
                elbow_l = (lm["LEFT_ELBOW"][0] * video.width, lm["LEFT_ELBOW"][1] * video.height)
                wrist_l = (lm["LEFT_WRIST"][0] * video.width, lm["LEFT_WRIST"][1] * video.height)
                angle_arm_l = calculate_angle(shoulder_l, elbow_l, wrist_l)

                hip_r = (lm["RIGHT_HIP"][0] * video.width, lm["RIGHT_HIP"][1] * video.height)
                knee_r = (lm["RIGHT_KNEE"][0] * video.width, lm["RIGHT_KNEE"][1] * video.height)
                ankle_r = (lm["RIGHT_ANKLE"][0] * video.width, lm["RIGHT_ANKLE"][1] * video.height)
                angle_leg_r = calculate_angle(hip_r, knee_r, ankle_r)

                hip_l = (lm["LEFT_HIP"][0] * video.width, lm["LEFT_HIP"][1] * video.height)
                knee_l = (lm["LEFT_KNEE"][0] * video.width, lm["LEFT_KNEE"][1] * video.height)
                ankle_l = (lm["LEFT_ANKLE"][0] * video.width, lm["LEFT_ANKLE"][1] * video.height)
                angle_leg_l = calculate_angle(hip_l, knee_l, ankle_l)

                # =============================
                # Registro de datos por frame
                # =============================
                session.record_frame_data(
                    frame_index=int(video.cap.get(cv2.CAP_PROP_POS_FRAMES)),
                    elapsed_time=session.elapsed_time(),
                    joints={
                        "shoulder_x_r": shoulder_r[0],
                        "shoulder_y_r": shoulder_r[1],
                        "elbow_x_r": elbow_r[0],
                        "elbow_y_r": elbow_r[1],
                        "wrist_x_r": wrist_r[0],
                        "wrist_y_r": wrist_r[1],
                        "angle_arm_r": angle_arm_r,
                        "shoulder_x_l": shoulder_l[0],
                        "shoulder_y_l": shoulder_l[1],
                        "elbow_x_l": elbow_l[0],
                        "elbow_y_l": elbow_l[1],
                        "wrist_x_l": wrist_l[0],
                        "wrist_y_l": wrist_l[1],
                        "angle_arm_l": angle_arm_l,
                        "hip_x_r": hip_r[0],
                        "hip_y_r": hip_r[1],
                        "knee_x_r": knee_r[0],
                        "knee_y_r": knee_r[1],
                        "ankle_x_r": ankle_r[0],
                        "ankle_y_r": ankle_r[1],
                        "angle_leg_r": angle_leg_r,
                        "hip_x_l": hip_l[0],
                        "hip_y_l": hip_l[1],
                        "knee_x_l": knee_l[0],
                        "knee_y_l": knee_l[1],
                        "ankle_x_l": ankle_l[0],
                        "ankle_y_l": ankle_l[1],
                        "angle_leg_l": angle_leg_l,
                    }
                )

                # =============================
                # Dibujo de resultados en pantalla
                # =============================
                detector.draw_landmarks(image, results)
                cv2.putText(image, f"Brazo D: {angle_arm_r}", (30, 50), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 0, 0), 2)
                cv2.putText(image, f"Brazo I: {angle_arm_l}", (30, 80), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 0, 0), 2)
                cv2.putText(image, f"Pierna D: {angle_leg_r}", (30, 110), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 0, 0), 2)
                cv2.putText(image, f"Pierna I: {angle_leg_l}", (30, 140), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 0, 0), 2)

            except KeyError:
                log_error("No se detectaron todos los puntos necesarios en este frame.")

        # =============================
        # Mostrar imagen y grabar frame
        # =============================
        cv2.imshow("Recon IA - Webcam", image)
        session.write_video_frame(image)

        # Salir con tecla 'q'
        if cv2.waitKey(10) & 0xFF == ord("q"):
            break

    # =============================
    # Finalización y guardado
    # =============================
    video.release()
    detector.release()
    session.close_session()
    cv2.destroyAllWindows()
    log_info("Captura finalizada correctamente.")


if __name__ == "__main__":
    main()