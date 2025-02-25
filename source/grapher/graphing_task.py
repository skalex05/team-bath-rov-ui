from PyQt6.QtCore import QRunnable
from typing import Callable


class GraphingTask(QRunnable):
    def __init__(self, func: Callable, callback: Callable):
        super().__init__()
        self.func = func
        self.callback = callback

    def run(self):
        self.callback(self.func())
