from PyQt6.QtCore import QRunnable
from typing import Callable


class GraphingTask(QRunnable):
    def __init__(self, func: Callable):
        super().__init__()
        self.func = func

    def run(self):
        self.func()
