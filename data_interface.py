import io
import sys
from collections import deque
from collections.abc import Sequence
from threading import Thread
from time import sleep
from random import random, randint
from typing import TYPE_CHECKING
from video_stream import VideoStream

import numpy as np
from PyQt6.QtGui import QImage

from vector3 import Vector3

if TYPE_CHECKING:
    from window import Window
    from app import App


# Temp function for generating a random float (optionally rounded to 'dp' decimal places)
def rand_float_range(a: int | float, b: int | float, dp: int = None):
    return round(a + random() * (b - a), dp)


def rand_vector3(a: int | float, b: int | float, dp: int = None):
    return Vector3(
        rand_float_range(a, b, dp),
        rand_float_range(a, b, dp),
        rand_float_range(a, b, dp)
    )

class DataInterface(Thread):
    """
        Stores information about the ROV/Float/Etc.
        This information is updated concurrently within the program inside this class's 'run' method.
    """

    def __init__(self, app: "App", windows: Sequence["Window"],
                 redirect_stdout: io.StringIO, redirect_stderr: io.StringIO):
        super().__init__()
        self.app = app
        self.windows = windows
        self.camera_feed_count = 1

        # This is where anything printed to the screen will be redirected to, so it can be copied into the UI
        self.redirect_stdout = redirect_stdout
        self.redirect_stderr = redirect_stderr
        self.lines_to_add = deque(maxlen=10)  # Queue of lines that need to be appended to the UI

        # Interface attributes:

        self.attitude = Vector3(0, 0, 0)  # pitch, yaw, roll
        self.angular_acceleration = Vector3(0, 0, 0)
        self.angular_velocity = Vector3(0, 0, 0)
        self.acceleration = Vector3(0, 0, 0)
        self.velocity = Vector3(0, 0, 0)
        self.depth = 0
        self.ambient_temperature = 0
        self.ambient_pressure = 0
        self.internal_temperature = 0

        self.main_sonar = 0
        self.FL_sonar = 0
        self.FR_sonar = 0
        self.BR_sonar = 0
        self.BL_sonar = 0

        self.actuator_1 = 0
        self.actuator_2 = 0
        self.actuator_3 = 0
        self.actuator_4 = 0
        self.actuator_5 = 0
        self.actuator_6 = 0

        self.SMART_repeater_temperature = 0
        self.MATE_float_depth = 0

        self.camera_feeds: [VideoStream] = [VideoStream(i) for i in range(self.camera_feed_count)]

    def run(self):
        while not self.app.closing:
            # Get new values for interface attributes:

            self.attitude = Vector3(
                rand_float_range(-45, 45, 1),
                rand_float_range(0, 360, 1),
                rand_float_range(-5, 5, 1)
            )
            self.angular_acceleration = rand_vector3(-1, 1, 2)
            self.angular_velocity = rand_vector3(-5, 5, 2)
            self.acceleration = rand_vector3(-1, 1, 2)
            self.velocity = rand_vector3(-5, 5, 2)
            self.depth = rand_float_range(0.5, 2.5, 2)
            self.ambient_temperature = rand_float_range(23, 27, 2)
            self.ambient_pressure = rand_float_range(18, 21, 2)
            self.internal_temperature = rand_float_range(40, 70, 1)

            self.main_sonar = rand_float_range(0, 500, 1)
            self.FL_sonar = rand_float_range(0, 500, 1)
            self.FR_sonar = rand_float_range(0, 500, 1)
            self.BR_sonar = rand_float_range(0, 500, 1)
            self.BL_sonar = rand_float_range(0, 500, 1)

            self.actuator_1 = randint(0, 100)
            self.actuator_2 = randint(0, 100)
            self.actuator_3 = randint(0, 100)
            self.actuator_4 = randint(0, 100)
            self.actuator_5 = randint(0, 100)
            self.actuator_6 = randint(0, 100)

            self.SMART_repeater_temperature = rand_float_range(23, 27, 2)
            self.MATE_float_depth = rand_float_range(0.5, 2.5, 2)

            for i in range(self.camera_feed_count):
                self.camera_feeds[i].update_camera_frame()

            # Process redirected stdout
            self.redirect_stdout.flush()
            lines = self.redirect_stdout.getvalue().splitlines()
            for line in lines:
                self.lines_to_add.append(line)
                print(line, file=sys.__stdout__)
            self.redirect_stdout.seek(0)
            self.redirect_stdout.truncate(0)

            # Process redirected stderr
            self.redirect_stderr.flush()
            lines = self.redirect_stderr.getvalue().splitlines()
            for line in lines:
                self.lines_to_add.append(line)
                print(line, file=sys.__stderr__)
            self.redirect_stderr.seek(0)
            self.redirect_stderr.truncate(0)

            # Inform each window that it should update its data
            for window in self.windows:
                window.on_update.emit()

            sleep(0.1)  # Release thread temporarily
