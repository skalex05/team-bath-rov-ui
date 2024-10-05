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
        self.data_interface: DataInterface | None = None
        self.closing = False

    def init_data_interface(self, windows: Sequence[Window], redirect_stdout, redirect_stderr):
        self.data_interface = DataInterface(self, windows, redirect_stdout, redirect_stderr)
        for window in windows:
            window.data = self.data_interface
        self.data_interface.start()


    def close(self):
        self.closing = True
        # Rejoin threads before closing
        try:
            self.data_interface.join(10)
        except ThreadError:
            print("Could not close data interface thread.")
        self.quit()
