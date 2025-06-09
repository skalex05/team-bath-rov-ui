from typing import TYPE_CHECKING

from PyQt6.QtGui import QScreen

from datainterface.data_interface import DataInterface
from nav_bar.nav_bar import NavBar

if TYPE_CHECKING:
    from app import App

from PyQt6 import uic
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QFrame


class Window(QFrame):
    """
        A custom container for each of the window's that will be displayed in the ROV UI.
        Allows for consistent styling of the windows.
        Specific windows should inherit this class for proper usage.
    """
    def __init__(self, file_path: str, app: "App", screen: QScreen):
        super().__init__()
        self.nav: NavBar | None = None
        self.app = app
        self.data: DataInterface | None = None
        self.desired_monitor = screen  # When undocked, this window will be displayed on this monitor
        # Load a .ui file into this window
        uic.loadUi(file_path, self)
        # Position the window and remove the default window frame
        self.setWindowFlag(Qt.WindowType.FramelessWindowHint)
        self.setGeometry(screen.availableGeometry())
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, False)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground, False)

    def attach_nav_bar(self, dock) -> None:
        self.nav = NavBar(self, dock)
        self.nav.generate_layout()

    def attach_data_interface(self) -> None:
        self.data = self.app.data_interface

    def closeEvent(self, e):
        self.app.close()
