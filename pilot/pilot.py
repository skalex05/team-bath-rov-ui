import os

from PyQt6 import uic
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QMainWindow
from screeninfo.common import Monitor

path_dir = os.path.dirname(os.path.realpath(__file__))


class Pilot(QMainWindow):
    def __init__(self, monitor: Monitor):
        super().__init__()
        uic.loadUi(f"{path_dir}\\pilot.ui", self)
        self.desired_monitor = monitor
        self.setGeometry(monitor.x, monitor.y, monitor.width, monitor.height)
        #self.setWindowFlag(Qt.WindowType.FramelessWindowHint)
