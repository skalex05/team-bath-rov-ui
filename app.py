from collections.abc import Sequence
from threading import ThreadError

from PyQt6.QtCore import pyqtSignal

from data_interface import DataInterface
from window import Window
from tasks.task import Task

from PyQt6.QtWidgets import QApplication, QWidget


class App(QApplication):
    """
        Class for storing about the overall application.
    """
    on_task_check = pyqtSignal(QWidget)

    def __init__(self, *args):
        super().__init__(*args)
        self.data_interface: DataInterface | None = None
        self.closing = False
        self.tasks: [Task] = [
            Task(self, "Install AUV docking station", "Move the ROV around and get used to the controls"),
            Task(self, "Place probiotic irrigation system in designated location",
                 "Here is another task that you need to do!", (2, 30)),
            Task(self, "Swim in a cirlce", "Sounds fun!", (3, 30)),
            Task(self, "Produce model of the shipwreck", "Sounds fun!", (5, 45)),
            Task(self, "Do a backflip", "Hell yeah!", (8, 30)),
            Task(self, "Perform a magic trick", "", (10, 10)),
            Task(self, "Deploy the MATE float and move it to the required location", "Nice", (11, 30)),
            Task(self, "Recieve the first set of readings for submersion", "Cool This is very interesting stuff",
                 (12, 0)),
            Task(self, "Recieve the second set of readings for submersion", "Cool This is very interesting stuff",
                 (13, 30)),
            Task(self, "Return to the surface", "Rahhhh", (13, 0)),
            Task(self, "Return to base", "Quickly!", (14, 0))
        ]
        self.tasks = list(sorted(self.tasks, key=lambda t: t.start_time[0] * 60 + t.start_time[1]))

    def reset_task_completion(self):
        for task in self.tasks:
            task.completed = False

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
