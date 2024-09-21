from PyQt6.QtWidgets import QStackedWidget
from PyQt6.QtCore import Qt

class Dock(QStackedWidget):
    def __init__(self, monitor, monitor_count):
        super().__init__()
        self.setGeometry(monitor.x, monitor.y, monitor.width, monitor.height)
        self.setFixedSize(1920, 1080)
        self.widgetRemoved.connect(self.on_dock_change)
        self.currentChanged.connect(lambda _: self.setWindowTitle(self.currentWidget().windowTitle()))
        self.setWindowFlag(Qt.WindowType.FramelessWindowHint)

        self.dockable = monitor_count > 1


    def on_dock_change(self):
        for i in range(self.count()):
            window = self.widget(i)
            window.nav.clear_layout()
            window.nav.generate_layout()
            window.nav.show()