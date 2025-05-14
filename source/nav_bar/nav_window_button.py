from typing import TYPE_CHECKING

from PyQt6.QtWidgets import QPushButton

if TYPE_CHECKING:
    from nav_bar.nav_bar import NavBar
    from window import Window


class NavWindowButton(QPushButton):
    """
        A Button which will switch the docked window's focus to this button's associated window.
    """
    def __init__(self, assoc_window: "Window", nav_bar: "NavBar"):
        super().__init__(assoc_window.windowTitle())
        self.assoc_window = assoc_window
        self.nav_bar = nav_bar
        self.setStyleSheet("""background-color:rgb(50,50,50); color: white;""")

    def on_click(self) -> None:
        # Change currently visible window
        self.nav_bar.dock.setCurrentWidget(self.assoc_window)
