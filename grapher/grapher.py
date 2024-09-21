import os

from data_interface import DataInterface

from PyQt6 import uic
from PyQt6.QtWidgets import QFrame
from PyQt6.QtCore import Qt

path_dir = os.path.dirname(os.path.realpath(__file__))


class Grapher(QFrame):
    def __init__(self, monitor):
        super().__init__()
        self.desired_monitor = monitor  # When undocked, this window will be displayed on this monitor

        self.setFixedSize(1920, 1080)
        uic.loadUi(f"{path_dir}\\grapher.ui", self)
        self.setGeometry(monitor.x, monitor.y, monitor.width, monitor.height)
        self.setWindowFlag(Qt.WindowType.FramelessWindowHint)

    def update_data(self, data: DataInterface):
        print(data.ambient_temperature)

