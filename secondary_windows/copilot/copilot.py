import os

from PyQt6 import uic
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QFrame

path_dir = os.path.dirname(os.path.realpath(__file__))


class Copilot(QFrame):
    def __init__(self, monitor):
        super().__init__()
        self.desired_monitor = monitor  # When undocked, this window will be displayed on this monitor
        self.setFixedSize(1920, 1080)
        uic.loadUi(f"{path_dir}\\copilot.ui", self)

        self.setGeometry(monitor.x, monitor.y, monitor.width, monitor.height)
        self.setWindowFlag(Qt.WindowType.FramelessWindowHint)

