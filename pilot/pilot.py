import os

from PyQt6.QtWidgets import QLabel

from data_interface import DataInterface
from window import Window

path_dir = os.path.dirname(os.path.realpath(__file__))


class Pilot(Window):
    def __init__(self, *args):
        super().__init__(f"{path_dir}\\pilot.ui", *args)

        self.data : DataInterface | None = None

        self.main_cam: QLabel = self.findChild(QLabel, "MainCameraView")
        self.secondary_1_cam: QLabel = self.findChild(QLabel, "SecondaryCameraView1")
        self.secondary_2_cam: QLabel = self.findChild(QLabel, "SecondaryCameraView2")

    def update_data(self):
        frame = self.data.camera_feeds[0]
        if frame.camera_frame:
            rect = self.main_cam.geometry()
            self.main_cam.setPixmap(frame.generate_pixmap(rect.width(), rect.height()))
        else:
            self.main_cam.setText("Main Camera Is Unavailable")

        frame = self.data.camera_feeds[0]
        if frame.camera_frame:
            rect = self.main_cam.geometry()
            self.main_cam.setPixmap(frame.generate_pixmap(rect.width(), rect.height()))
        else:
            self.main_cam.setText("Main Camera Is Unavailable")

        frame = self.data.camera_feeds[0]
        if frame.camera_frame:
            rect = self.secondary_1_cam.geometry()
            self.secondary_1_cam.setPixmap(frame.generate_pixmap(rect.width(), rect.height()))
        else:
            self.secondary_1_cam.setText("Secondary Cam 1 Is Unavailable")

        frame = self.data.camera_feeds[0]
        if frame.camera_frame:
            rect = self.secondary_2_cam.geometry()
            self.secondary_2_cam.setPixmap(frame.generate_pixmap(rect.width(), rect.height()))
        else:
            self.secondary_2_cam.setText("Secondary Cam 2 Is Unavailable")

