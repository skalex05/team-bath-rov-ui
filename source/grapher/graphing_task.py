from PyQt6.QtCore import QRunnable
from typing import Callable


class GraphingTask(QRunnable):
    def __init__(self, func: Callable, callback: Callable = None):
        super().__init__()
        self.func = func
        self.callback = callback

    def run(self):
        if self.callback:
            self.callback(self.func())
        else:
            self.func()
