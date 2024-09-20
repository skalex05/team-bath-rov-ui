from PyQt6.QtWidgets import QPushButton


class NavWindowButton(QPushButton):
    def __init__(self, assoc_window, nav_bar):
        super().__init__(assoc_window.windowTitle())
        self.assoc_window = assoc_window
        self.nav_bar = nav_bar

    def on_click(self):
        self.nav_bar.dock.setCurrentWidget(self.assoc_window)