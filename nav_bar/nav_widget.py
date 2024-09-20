from PyQt6.QtWidgets import QWidget, QHBoxLayout, QPushButton
from nav_bar.nav_window_button import NavWindowButton


class NavBar(QWidget):
    def __init__(self, parent_window, dock=None):
        super().__init__(parent_window)
        self.dockable_widget = None
        self.docked = True
        self.dock = dock

        self.parent_window = parent_window

        self.layout = QHBoxLayout()
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(self.layout)

    def generate_layout(self):
        if self.dock is None:
            return
        single = True
        if self.docked:
            print(self.parent_window.windowTitle())
            for i in range(self.dock.count()):
                window = self.dock.widget(i)
                print(window.windowTitle(), window.nav.docked)
                if window == self.parent_window or not window.nav.docked:
                    continue
                single = False
                switch_button = NavWindowButton(window, self)
                switch_button.clicked.connect(switch_button.on_click)
                self.layout.addWidget(switch_button)

        if not (single and self.docked):
            self.dockable_widget = QPushButton("Undock" if self.docked else "Dock")
            self.dockable_widget.setMaximumWidth(80)
            self.dockable_widget.clicked.connect(lambda _: self.f_undock() if self.docked else self.f_dock())
            self.layout.addWidget(self.dockable_widget)

        self.setLayout(self.layout)

    def clear_layout(self, layout=None):
        if layout is None:
            layout = self.layout
        while layout.count() > 0:
            i = layout.takeAt(0)
            w = i.widget()
            if w is not None:
                w.deleteLater()
            else:
                self.clear_layout(i.layout())


    def f_dock(self):
        self.docked = True
        self.dock.addWidget(self.parent_window)
        self.dock.on_dock_change()
        self.dock.setCurrentWidget(self.parent_window)
        self.clear_layout()
        self.generate_layout()

    def f_undock(self):
        self.docked = False
        self.dock.removeWidget(self.parent_window)
        self.parent_window.setParent(None)
        self.parent_window.setGeometry(self.parent_window.desired_monitor.x+100,
                                       self.parent_window.desired_monitor.y+100,
                                       self.parent_window.geometry().width(),
                                       self.parent_window.geometry().height())
        self.clear_layout()
        self.generate_layout()

        self.parent_window.show()

