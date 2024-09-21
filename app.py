from collections.abc import Sequence
from threading import ThreadError

from data_interface import DataInterface
from window import Window

from PyQt6.QtWidgets import QApplication


class App(QApplication):
    """
        Class for storing about the overall application.
    """
    def __init__(self, *args):
        super().__init__(*args)
        self.interface = None
        self.closing = False

    def init_data_interface(self, windows: Sequence[Window]):
        self.interface = DataInterface(self, windows)
        self.interface.start()

    def close(self):
        self.closing = True
        # Rejoin threads before closing
        try:
            self.interface.join(10)
        except ThreadError:
            print("Could not close data interface thread.")
        self.quit()
