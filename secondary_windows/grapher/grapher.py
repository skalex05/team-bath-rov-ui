import os

from PyQt6 import uic
from PyQt6.QtWidgets import QWidget
from PyQt6.QtCore import Qt

path_dir = os.path.dirname(os.path.realpath(__file__))


class Grapher(QWidget):
    def __init__(self, desired_monitor):
        super().__init__()
        self.desired_monitor = desired_monitor  # When undocked, this window will be displayed on this monitor
        #self.setWindowFlag(Qt.WindowType.FramelessWindowHint)
        uic.loadUi(f"{path_dir}\\grapher.ui", self)
