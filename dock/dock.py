from PyQt6.QtWidgets import QStackedWidget

class Dock(QStackedWidget):
    def __init__(self, monitor):
        super().__init__()
        self.setGeometry(monitor.x, monitor.y, monitor.width, monitor.height)
        self.widgetRemoved.connect(self.on_dock_change)
        self.currentChanged.connect(lambda _: self.setWindowTitle(self.currentWidget().windowTitle()))

    def on_dock_change(self):
        print("docked\n\n\n")
        print(self.count())
        for i in range(self.count()):
            window = self.widget(i)
            print("update", window.windowTitle())
            window.nav.clear_layout()
            window.nav.generate_layout()
            window.nav.show()