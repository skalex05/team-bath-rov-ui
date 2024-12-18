import sys
from time import time, sleep
from threading import Thread

import cv2
from PyQt6.QtGui import QImage, QPixmap


class VideoStream:
    max_attempts = 5

    def __init__(self, index):
        self.camera_frame = None
        self.camera_feed = None
        self.init_thread = None
        self.index = index
        self.width = -1
        self.height = -1
        self.channels = -1
        self.initialising = False
        self.initialised = False
        self.init_attempts = 0
        self.start_init_camera_feed()

    def start_init_camera_feed(self):
        if self.initialising:
            return
        self.initialising = True
        self.initialised = False
        self.init_attempts = 0
        self.init_thread = Thread(target=self.init_camera_feed, daemon=True)
        self.init_thread.start()

    def init_camera_feed(self):
        print(f"Initialising Cam {self.index + 1}")
        self.camera_feed = cv2.VideoCapture(self.index)
        ret, frame = self.camera_feed.read()
        if ret:
            self.height, self.width, self.channels = frame.shape
            print(f"Cam {self.index + 1} initialised successfully!")
            self.initialising = False
            self.camera_frame = frame
            self.initialised = True
        else:
            print(f"Could not read from Cam {self.index + 1}")
            self.camera_feed = None
            if self.init_attempts < VideoStream.max_attempts:
                self.init_attempts += 1
                print(f"Retrying... Attempt {self.init_attempts}/{self.max_attempts}")
                sleep(5)
                self.init_camera_feed()
            else:
                self.initialising = False
                print(f"Failed to connect to Cam {self.index + 1}")
            return

    def update_camera_frame(self):
        if self.camera_feed is None:
            return
        ret, frame = self.camera_feed.read()
        if not ret:
            print(f"Could not read from Cam {self.index + 1}")
            self.camera_feed = None
            return

        self.camera_frame = frame

    @staticmethod
    def generate_pixmap(camera_frame, target_width, target_height):
        pixmap = QPixmap.fromImage(camera_frame)
        # Ensure image fits available space as best as possible.
        pixmap = pixmap.scaledToHeight(target_height)
        if pixmap.width() > target_width:
            pixmap = pixmap.scaledToWidth(target_width)
        return pixmap
