import cv2

class VideoCaptureManager:
    """
    Gestiona la apertura, lectura y grabación de vídeo o webcam.
    Permite recuperar FPS, dimensiones y configurar el grabador de salida.
    """

    def __init__(self, source=0):
        """
        Parámetros:
        -----------
        source : int o str
            0 -> Webcam predeterminada
            "ruta/video.mp4" -> Archivo de vídeo local
        """
        self.cap = cv2.VideoCapture(source, cv2.CAP_AVFOUNDATION)   
        if not self.cap.isOpened():
            raise RuntimeError(f"No se pudo abrir la fuente de vídeo: {source}")

        # Propiedades básicas del vídeo
        self.fps = round(self.cap.get(cv2.CAP_PROP_FPS)) or 30
        self.width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        self.height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        self.frame_size = (self.width, self.height)
        print(f"[VideoCaptureManager] Fuente abierta: {source} ({self.width}x{self.height} @ {self.fps}fps)")

        self.video_writer = None

    def read_frame(self):
        """
        Lee un frame del vídeo/cámara.

        Retorna:
        --------
        (bool, np.ndarray)
            - ret: True si se pudo leer correctamente.
            - frame: imagen capturada (BGR).
        """
        return self.cap.read()


    def create_writer(self, output_path):
        """
        Configura el grabador de vídeo (VideoWriter) para guardar la salida procesada.

        Parámetros:
        -----------
        output_path : str
            Ruta del archivo de salida (MP4 recomendado).
        """
        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        self.video_writer = cv2.VideoWriter(output_path, fourcc, self.fps, self.frame_size)
        print(f"[VideoCaptureManager] Grabador creado en {output_path}")

    def write_frame(self, frame):
        """Escribe un frame en el archivo de salida."""
        if self.video_writer:
            self.video_writer.write(frame)

    def release(self):
        """Libera la cámara y el escritor de vídeo."""
        if self.cap:
            self.cap.release()
        if self.video_writer:
            self.video_writer.release()
        print("[VideoCaptureManager] Recursos liberados correctamente.")
