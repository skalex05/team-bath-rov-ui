from time import time

import cv2
import numpy as np
from PyQt6.QtGui import QImage, QPixmap


class VideoStream:
    max_attempts = 10
    def __init__(self, index):
        self.camera_frame = None
        self.camera_feed = None
        self.index = index
        self.width = -1
        self.height = -1
        self.channels = -1
        self.init_camera_feed()
        self.init_attempts = 0

    def init_camera_feed(self):
        print(f"Initialising Cam {self.index + 1}")
        self.camera_feed = cv2.VideoCapture(self.index)
        ret, frame = self.camera_feed.read()
        if not ret:
            print(f"Could not read from Cam {self.index + 1}")
            self.camera_feed = None
            return
        self.height, self.width, self.channels = frame.shape

    def update_camera_frame(self):
        self.time = time()
        if self.camera_feed is None:
            return
        ret, frame = self.camera_feed.read()
        if not ret:
            print(f"Could not read from Cam {self.index + 1}")
            self.camera_feed = None
            return
        self.camera_frame = QImage(frame,
                                   self.width, self.height, self.width * self.channels, QImage.Format.Format_BGR888)

    def generate_pixmap(self, target_width, target_height):
        pixmap = QPixmap.fromImage(self.camera_frame)
        # Ensure image fits available space as best as possible.
        pixmap = pixmap.scaledToHeight(target_height)
        if pixmap.width() > target_width:
            pixmap = pixmap.scaledToWidth(target_width)
        return pixmap
