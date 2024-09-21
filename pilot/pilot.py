import os

from data_interface import DataInterface

from PyQt6 import uic
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QFrame
from screeninfo.common import Monitor

path_dir = os.path.dirname(os.path.realpath(__file__))


class Pilot(QFrame):
    def __init__(self, monitor: Monitor):
        super().__init__()
        self.desired_monitor = monitor

        self.setFixedSize(1920, 1080)
        uic.loadUi(f"{path_dir}\\pilot.ui", self)
        self.setGeometry(monitor.x, monitor.y, monitor.width, monitor.height)
        self.setWindowFlag(Qt.WindowType.FramelessWindowHint)

    def update_data(self, data: DataInterface):
        pass
        #print(data.ambient_temperature)
