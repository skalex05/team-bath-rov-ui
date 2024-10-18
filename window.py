from typing import TYPE_CHECKING

from nav_bar.nav_bar import NavBar

if TYPE_CHECKING:
    from app import App

from PyQt6 import uic
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import QFrame
from screeninfo.common import Monitor


class Window(QFrame):
    """
        A custom container for each of the window's that will be displayed in the ROV UI.
        Allows for consistent styling of the windows.
        Specific windows should inherit this class for proper usage.
    """
    on_update = pyqtSignal()
    def __init__(self, file, app: "App", monitor: Monitor):
        super().__init__()
        self.nav = None
        self.app = app
        self.desired_monitor = monitor  # When undocked, this window will be displayed on this monitor
        # Set window size and load content
        self.setFixedSize(1920, 1080)
        # Load a .ui file into this window
        uic.loadUi(file, self)
        # Position the window and remove the default window frame
        self.setGeometry(monitor.x, monitor.y, monitor.width, monitor.height)
        self.setWindowFlag(Qt.WindowType.FramelessWindowHint)
        self.on_update.connect(self.update_data)

    def attach_nav_bar(self, dock):
        self.nav = NavBar(self, dock)
        self.nav.generate_layout()

    def update_data(self):
        # Each subclass should override this to fit their content
        pass

    def closeEvent(self, e):
        self.app.close()

