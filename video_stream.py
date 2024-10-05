import cv2
from PyQt6.QtGui import QImage, QPixmap


class VideoStream:
    def __init__(self, index):
        self.camera_frame = None
        self.index = index
        self.camera_feed = None

        self.init_camera_feed()

    def init_camera_feed(self):
        print(f"Initialising Cam {self.index + 1}")
        self.camera_feed = cv2.VideoCapture(self.index)
        self.update_camera_frame(True)

    def update_camera_frame(self, ignore_none=False):
        if not ignore_none and self.camera_feed is None:
            self.init_camera_feed()
            return
        ret, frame = self.camera_feed.read()
        if not ret:
            print(f"Could not read from Cam {self.index + 1}")
            self.camera_feed = None
            return

        height, width, channels = frame.shape

        self.camera_frame = QImage(frame.data, width, height, width * channels, QImage.Format.Format_BGR888)

    def generate_pixmap(self, target_width, target_height):
        pixmap = QPixmap.fromImage(self.camera_frame)
        # Ensure image fits available space as best as possible.
        pixmap = pixmap.scaledToHeight(target_height)
        if pixmap.width() > target_width:
            pixmap = pixmap.scaledToWidth(target_width)
        return pixmap
