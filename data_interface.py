from collections.abc import Sequence
from threading import Thread
from time import sleep
from random import random
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from window import Window
    from app import App


# Temp function for generating a random float (optionally rounded to 'dp' decimal places)
def rand_float_range(a: int | float, b: int | float, dp: int = None):
    return round(a + random() * (b - a), dp)


class DataInterface(Thread):
    """
        Stores information about the ROV/Float/Etc.
        This information is updated concurrently within the program inside this class's 'run' method.
    """
    def __init__(self, app: "App", windows: Sequence["Window"]):
        super().__init__()
        self.app = app
        self.windows = windows

        # Interface attributes:
        self.ambient_temperature = 0
        self.ambient_pressure = 0

    def run(self):
        while not self.app.closing:
            # Get new values for interface attributes:

            self.ambient_temperature = rand_float_range(23, 27, 2)
            self.ambient_pressure = rand_float_range(18, 21, 2)

            # Inform each window that it should update its data
            for window in self.windows:
                window.update_data(self)

            sleep(0.1)  # Release thread temporarily
