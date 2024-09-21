from threading import Thread, ThreadError
from time import sleep
from random import random

def rand_float_range(a,b, dp=None):
    return round(a + random()*(b-a),dp)

class DataInterface(Thread):
    def __init__(self, app, windows):
        super().__init__()
        self.app = app
        self.windows = windows
        self.ambient_temperature = 0

    def run(self):
        while not self.app.closing:
            self.ambient_temperature = rand_float_range(22, 25, 2)

            for window in self.windows:
                window.update_data(self)

            sleep(0.1)
