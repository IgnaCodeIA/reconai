import cv2

from core.logger import get_logger

log = get_logger("core.video_capture")


class VideoCaptureManager:
    """Wrapper around cv2.VideoCapture that owns an optional VideoWriter for output."""

    def __init__(self, source=0):
        self.cap = cv2.VideoCapture(source, cv2.CAP_AVFOUNDATION)
        if not self.cap.isOpened():
            raise RuntimeError(f"Could not open video source: {source}")

        self.fps = round(self.cap.get(cv2.CAP_PROP_FPS)) or 30
        self.width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        self.height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        self.frame_size = (self.width, self.height)
        log.info(
            "Video source opened: %s (%dx%d @ %dfps)",
            source, self.width, self.height, self.fps
        )

        self.video_writer = None

    def read_frame(self):
        """Read the next frame from the capture device. Returns (ret, frame)."""
        return self.cap.read()

    def create_writer(self, output_path):
        """Create an mp4 VideoWriter at output_path using the source's fps and frame size."""
        log.debug("create_writer called with output_path=%s", output_path)
        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        self.video_writer = cv2.VideoWriter(output_path, fourcc, self.fps, self.frame_size)
        log.info("Writer created at %s", output_path)

    def write_frame(self, frame):
        """Write a frame to the output writer if one was created."""
        if self.video_writer:
            self.video_writer.write(frame)

    def release(self):
        """Release the underlying capture and writer resources."""
        if self.cap:
            self.cap.release()
        if self.video_writer:
            self.video_writer.release()
        log.info("Resources released")
