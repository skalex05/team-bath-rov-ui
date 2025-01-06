import math
import time
from typing import TYPE_CHECKING

from PyQt6.QtCore import QRect, QPoint
from PyQt6.QtWidgets import QWidget, QHBoxLayout, QLayout, QPushButton

from dock import Dock
from nav_bar.nav_window_button import NavWindowButton

if TYPE_CHECKING:
    from window import Window


class NavBar(QWidget):
    """
        A Navigation bar that is displayed at the top of each window.
        Allows windows to be docked/undocked/closed/dragged as well as for switching view from within a dock.
    """

    def __init__(self, parent_window: "Window", dock: Dock, widget_width: int = 80):
        super().__init__(parent_window)
        self.close_button_widget = None
        self.minimise_widget = None
        self.buttons = None
        self.dockable_widget = None  # Button that says either dock/undock
        self.docked = True  # Check if the parent window of this nav bar is docked/undocked
        self.dock = dock  # A reference to the dock window object
        self.app = parent_window.app

        self.parent_window = parent_window
        self.top_window = dock

        self.widget_width = widget_width
        self.layout = QHBoxLayout()
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(self.layout)

    def generate_layout(self):
        if self.dock is None:
            return
        single = True
        # Only allow view switching if the window is docked
        if self.docked:
            for i in range(self.dock.count()):
                window = self.dock.widget(i)
                if window == self.parent_window or not window.nav.docked:
                    continue
                single = False
                switch_button = NavWindowButton(window, self)
                switch_button.clicked.connect(switch_button.on_click)
                self.layout.addWidget(switch_button)

        # If there is more than one window in the app and if more than one window is available.
        # Then the window can be docked/undocked
        if not (single and self.docked) and self.dock.is_dockable():
            self.dockable_widget = QPushButton("Undock" if self.docked else "Dock")
            self.dockable_widget.setMaximumWidth(80)
            self.dockable_widget.clicked.connect(lambda _: self.f_undock() if self.docked else self.f_dock())
            self.layout.addWidget(self.dockable_widget)

        # Add button for minimising
        self.minimise_widget = QPushButton("Minimise")
        self.minimise_widget.setMaximumWidth(80)
        self.minimise_widget.clicked.connect(self.minimise)
        self.layout.addWidget(self.minimise_widget)

        # Add button for closing the program
        self.close_button_widget = QPushButton("Close")
        self.close_button_widget.setMaximumWidth(80)
        def on_close():
            self.app.close()

        self.close_button_widget.clicked.connect(on_close)
        self.layout.addWidget(self.close_button_widget)

        self.buttons = QWidget(self)
        x_offset = self.parent_window.width() - self.widget_width * self.layout.count()
        self.buttons.setGeometry(QRect(x_offset, 0, self.widget_width * self.layout.count(), self.geometry().height()))

        self.buttons.setLayout(self.layout)

        # Adjust size of the navbar depending on how many buttons are in the layout.
        self.setGeometry(QRect(0, 0, self.parent_window.geometry().width(), self.geometry().height()))

        self.buttons.show()

    def clear_layout(self, layout: QLayout = None):
        # Remove all windows in the  layout
        if layout is None:
            layout = self.layout
        while layout.count() > 0:
            i = layout.takeAt(0)
            w = i.widget()
            if w is not None:
                w.deleteLater()
            else:
                self.clear_layout(i.layout())

    def minimise(self):
        self.top_window.showMinimized()

    def f_dock(self):
        # Called when the dock button is pressed
        self.docked = True
        # Add the window associated with this nav bar to the dock
        self.top_window = self.dock
        self.dock.addWidget(self.parent_window)
        # Update windows in the dock
        self.dock.on_dock_change()
        # Set this nav bar's parent window to be at the top of the stack
        self.dock.setCurrentWidget(self.parent_window)

    def f_undock(self):
        self.docked = False
        self.dock.removeWidget(self.parent_window)
        self.top_window = self.parent_window
        self.parent_window.setParent(None)
        self.parent_window.setGeometry(self.parent_window.desired_monitor.availableGeometry())
        self.parent_window.showFullScreen()
        self.clear_layout()
        self.generate_layout()

        self.parent_window.show()

    def mouseReleaseEvent(self, event):
        chosen_screen = self.app.screens()[0]
        x, y = (event.globalPosition().x(), event.globalPosition().y())
        for screen in self.app.screens():
            geom = screen.geometry()
            if geom.x() <= x <= geom.x()+geom.width() and geom.y() <= y <= geom.y()+geom.height():
                chosen_screen = screen
                break

        self.top_window.setGeometry(chosen_screen.geometry())
        self.clear_layout()
        self.generate_layout()
