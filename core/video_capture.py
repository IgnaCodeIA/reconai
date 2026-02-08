import cv2

class VideoCaptureManager:

    def __init__(self, source=0):
        self.cap = cv2.VideoCapture(source, cv2.CAP_AVFOUNDATION)   
        if not self.cap.isOpened():
            raise RuntimeError(f"No se pudo abrir la fuente de vídeo: {source}")

        self.fps = round(self.cap.get(cv2.CAP_PROP_FPS)) or 30
        self.width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        self.height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        self.frame_size = (self.width, self.height)
        print(f"[VideoCaptureManager] Fuente abierta: {source} ({self.width}x{self.height} @ {self.fps}fps)")

        self.video_writer = None

    def read_frame(self):
        return self.cap.read()

    def create_writer(self, output_path):
        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        self.video_writer = cv2.VideoWriter(output_path, fourcc, self.fps, self.frame_size)
        print(f"[VideoCaptureManager] Grabador creado en {output_path}")

    def write_frame(self, frame):
        if self.video_writer:
            self.video_writer.write(frame)

    def release(self):
        if self.cap:
            self.cap.release()
        if self.video_writer:
            self.video_writer.release()
        print("[VideoCaptureManager] Recursos liberados correctamente.")