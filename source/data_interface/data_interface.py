import io
import pickle
import sys
from collections import deque
from collections.abc import Sequence
from socket import socket, AF_INET, SOCK_DGRAM
from threading import Thread
from typing import TYPE_CHECKING
import time

from PyQt6.QtCore import pyqtSignal, QObject

from float_data import FloatData
from rov_data import ROVData
from video_stream import VideoStream
from data_interface.vector3 import Vector3

if TYPE_CHECKING:
    from window import Window
    from app import App

class DataInterface(QObject):
    """
        Stores information about the ROV/Float/Etc.
        This information is updated concurrently within the program inside this class's 'run' method.
    """
    rov_data_update = pyqtSignal()
    float_data_update = pyqtSignal()
    video_stream_update = pyqtSignal(int)
    stdout_update = pyqtSignal()

    def __init__(self, app: "App", windows: Sequence["Window"],
                 redirect_stdout: io.StringIO, redirect_stderr: io.StringIO):
        super().__init__()
        self.app = app
        self.windows = windows
        self.camera_feed_count = 1

        # This is where anything printed to the screen will be redirected to, so it can be copied into the UI
        self.redirect_stdout = redirect_stdout
        self.redirect_stderr = redirect_stderr

        # Stdout Data

        self.lines_to_add = deque(maxlen=10)  # Queue of lines that need to be appended to the UI

        # ROV Data

        self.rov_connected = False
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

        # MATE FLOAT Data
        self.float_connected = False
        self.float_depth = 0

        # Camera Feeds

        self.camera_feeds: [VideoStream] = []
        self.camera_threads: [Thread] = []
        # Start Threads

        for i in range(self.camera_feed_count):
            self.camera_feeds.append(VideoStream(i))
            cam_thread = Thread(target=self.f_video_stream_thread, args=(i,))
            self.camera_threads.append(cam_thread)
            cam_thread.start()

        self.rov_data_thread = Thread(target=self.f_rov_data_thread)
        self.rov_data_thread.start()

        self.float_data_thread = Thread(target=self.f_float_data_thread)
        self.float_data_thread.start()

        self.stdout_thread = Thread(target=self.f_stdout_thread)
        self.stdout_thread.start()

    def f_rov_data_thread(self):
        data_server = socket(AF_INET, SOCK_DGRAM)
        data_server.bind(("localhost", 52525))
        data_server.setblocking(False)
        data_server.settimeout(1)
        while not self.app.closing:
            try:
                payload_bytes, addr = data_server.recvfrom(1024)
            except TimeoutError:
                self.rov_connected = False
                self.rov_data_update.emit()
                continue
            self.rov_connected = True
            rov_data: ROVData = pickle.loads(payload_bytes)

            # Map all attributes in ROVData to their associated attributes in the DataInterface
            for attr in rov_data.__dict__:
                self.__setattr__(attr, rov_data.__getattribute__(attr))

            self.rov_data_update.emit()

            time.sleep(0.0167)

    def f_float_data_thread(self):
        data_server = socket(AF_INET, SOCK_DGRAM)
        data_server.bind(("localhost", 52526))
        data_server.setblocking(False)
        data_server.settimeout(1)
        while not self.app.closing:
            try:
                payload_bytes, addr = data_server.recvfrom(1024)
            except TimeoutError:
                self.float_connected = False
                self.float_data_update.emit()
                continue
            self.float_connected = True
            float_data: FloatData = pickle.loads(payload_bytes)

            # Map all attributes in ROVData to their associated attributes in the DataInterface
            for attr in float_data.__dict__:
                self.__setattr__(attr, float_data.__getattribute__(attr))

            self.float_data_update.emit()

    def f_video_stream_thread(self, i):
        while not self.app.closing:
            self.camera_feeds[i].update_camera_frame()
            self.video_stream_update.emit(i)
            time.sleep(0.0167)

    def f_stdout_thread(self):
        while not self.app.closing:
            # Process redirected stdout
            self.redirect_stdout.flush()
            update = False
            if self.redirect_stdout != sys.__stdout__:
                lines = self.redirect_stdout.getvalue().splitlines()
                for line in lines:
                    update = True
                    self.lines_to_add.append(line)
                    print(line, file=sys.__stdout__)
                self.redirect_stdout.seek(0)
                self.redirect_stdout.truncate(0)

            # Process redirected stderr
            self.redirect_stderr.flush()
            if self.redirect_stderr != sys.__stderr__:
                lines = self.redirect_stderr.getvalue().splitlines()
                for line in lines:
                    self.lines_to_add.append(line)
                    update = True
                    print(line, file=sys.__stderr__)
                self.redirect_stderr.seek(0)
                self.redirect_stderr.truncate(0)

            if update:
                self.stdout_update.emit()

            time.sleep(0.0167)

    def close(self):
        self.rov_data_thread.join(10)
        self.stdout_thread.join(10)
        for video_stream_thread in self.camera_threads:
            video_stream_thread.join(10)
