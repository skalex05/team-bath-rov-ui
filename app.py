from PyQt6.QtWidgets import QApplication

from data_interface import DataInterface, ThreadError

class App(QApplication):
    def __init__(self, *args):
        super().__init__(*args)
        self.interface = None
        self.closing = False

    def init_data_interface(self, windows):
        self.interface = DataInterface(self, windows)
        self.interface.start()

    def close(self):
        self.closing = True
        try:
            self.interface.join(10)
        except ThreadError:
            print("Could not close data interface thread.")
        self.quit()
