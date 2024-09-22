from typing import TYPE_CHECKING

from PyQt6.QtWidgets import QStackedWidget
from PyQt6.QtCore import Qt

if TYPE_CHECKING:
    from screeninfo import Monitor
    from app import App


class Dock(QStackedWidget):
    """
        Used to contain multiple windows within one.
        These window can be undocked and moved independently if the user desires.
        The NavBar can be used to select the visible window shown on the dock.
    """
    def __init__(self, app: "App", monitor: "Monitor", monitor_count):
        super().__init__()
        self.app = app

        # Create a frameless 1920x1080 window
        self.setGeometry(monitor.x, monitor.y, monitor.width, monitor.height)
        self.setFixedSize(1920, 1080)
        self.widgetRemoved.connect(self.on_dock_change)  # Will run when a window is docked/undocked
        # Update the dock's title to be the same as the currently visible window
        self.currentChanged.connect(lambda _: self.setWindowTitle(self.currentWidget().windowTitle()))
        self.setWindowFlag(Qt.WindowType.FramelessWindowHint)

        # Prevent undocking if only monitor is available
        self.dockable = monitor_count > 1

    def on_dock_change(self):
        for i in range(self.count()):
            # Regenerate the nav bar if a window has been docked/undocked
            window = self.widget(i)
            window.nav.clear_layout()
            window.nav.generate_layout()
            window.nav.show()

    def closeEvent(self, e):
        self.app.close()