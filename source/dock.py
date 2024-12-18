from typing import TYPE_CHECKING

from PyQt6.QtWidgets import QStackedWidget
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QScreen

if TYPE_CHECKING:
    from screeninfo import Monitor
    from app import App


class Dock(QStackedWidget):
    """
        Used to contain multiple windows within one.
        These window can be undocked and moved independently if the user desires.
        The NavBar can be used to select the visible window shown on the dock.
    """

    def __init__(self, app: "App", screen: QScreen):
        super().__init__()
        self.app = app

        # Create a frameless 1920x1080 window
        self.setGeometry(screen.availableGeometry())
        self.widgetRemoved.connect(self.on_dock_change)  # Will run when a window is docked/undocked
        # Update the dock's title to be the same as the currently visible window
        self.currentChanged.connect(self.on_current_window_change)
        self.setWindowFlag(Qt.WindowType.FramelessWindowHint)

    def is_dockable(self):
        return len(self.app.screens()) > 1

    def add_windows(self, *windows):
        for window in windows:
            self.addWidget(window)
        self.on_dock_change()

    def on_current_window_change(self):
        self.setWindowTitle(self.currentWidget().windowTitle())
        self.currentWidget().nav.clear_layout()
        self.currentWidget().nav.generate_layout()

    def on_dock_change(self):
        for i in range(self.count()):
            # Regenerate the nav bar if a window has been docked/undocked
            window = self.widget(i)
            window.nav.clear_layout()
            window.nav.generate_layout()
            window.nav.show()

    def closeEvent(self, e):
        self.app.close()
