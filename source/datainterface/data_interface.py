import io
import pickle
import sys
from threading import Thread

from sock_stream_recv import SockStreamRecv
from sock_stream_send import SockStreamSend
from typing import TYPE_CHECKING, Sequence
import pygame

from PyQt6.QtCore import pyqtSignal, QObject, QTimer
from PyQt6.QtGui import QImage

from float_data import FloatData
from rov_data import ROVData
from vector3 import Vector3
from stdout_type import StdoutType

if TYPE_CHECKING:
    from window import Window
    from app import App

ROV_IP = "localhost"
FLOAT_IP = "localhost"


class DataInterface(QObject):
    """
        Stores information about the ROV/Float/Etc.
        This information is updated concurrently within the program inside this class's 'run' method.
    """
    rov_data_update = pyqtSignal()
    float_data_update = pyqtSignal()
    video_stream_update = pyqtSignal(int)
    stdout_update = pyqtSignal(StdoutType, str)

    # ALERT SIGNALS
    attitude_alert = pyqtSignal()
    depth_alert = pyqtSignal()
    ambient_temperature_alert = pyqtSignal()
    ambient_pressure_alert = pyqtSignal()
    internal_temperature_alert = pyqtSignal()
    float_depth_alert = pyqtSignal()

    def __init__(self, app: "App", windows: Sequence["Window"],
                 redirect_stdout: io.StringIO, redirect_stderr: io.StringIO):
        super().__init__()
        self.app = app
        self.windows = windows
        self.camera_feed_count = 3

        # This is where anything printed to the screen will be redirected to, so it can be copied into the UI
        self.redirect_stdout = redirect_stdout
        self.redirect_stderr = redirect_stderr

        # ROV Data

        self.attitude = Vector3(0, 0, 0)  # pitch, yaw, roll
        self.angular_acceleration = Vector3(0, 0, 0)
        self.angular_velocity = Vector3(0, 0, 0)
        self.acceleration = Vector3(0, 0, 0)
        self.velocity = Vector3(0, 0, 0)
        self.depth = 0
        self.ambient_temperature = 0
        self.ambient_pressure = 0
        self.internal_temperature = 0
        self.cardinal_direction = 0
        self.grove_water_sensor = 0

        self.actuator_1 = 0
        self.actuator_2 = 0
        self.actuator_3 = 0
        self.actuator_4 = 0
        self.actuator_5 = 0
        self.actuator_6 = 0

        # MATE FLOAT Data
        self.float_depth = 0

        # Camera Feeds

        self.camera_feeds = []
        self.camera_threads: [Thread] = []

        # Controller State

        pygame.init()
        pygame.joystick.init()

        self.joystick = None

        # Start Threads
        def on_camera_feed_disconnect(i):
            self.camera_feeds[i] = None
            self.video_stream_update.emit(i)

        for i in range(self.camera_feed_count):
            self.camera_feeds.append(None)
            cam_thread = SockStreamRecv(self.app, ROV_IP, 52524-i,
                                        lambda payload_bytes, j=i, : self.on_video_stream_sock_recv(payload_bytes, j),
                                        lambda j=i: on_camera_feed_disconnect(j))
            self.camera_threads.append(cam_thread)
            cam_thread.start()

        self.rov_data_thread = SockStreamRecv(self.app, ROV_IP, 52525,  self.on_rov_data_sock_recv,
                                              lambda: self.rov_data_update.emit())
        self.rov_data_thread.start()

        self.float_data_thread = SockStreamRecv(self.app, ROV_IP, 52625, self.on_float_data_sock_recv,
                                                lambda: self.float_data_update.emit())
        self.float_data_thread.start()

        self.stdout_ui_thread = Thread(target=self.f_stdout_ui_thread)
        self.stdout_ui_thread.start()

        self.stdout_sock_thread = SockStreamRecv(self.app, ROV_IP, 52535,  self.on_stdout_sock_recv, None)
        self.stdout_sock_thread.start()

        self.controller_input_thread = SockStreamSend(self.app, ROV_IP, 52526, 0.01,
                                                      self.get_controller_input, None)
        self.controller_input_thread.start()

        # Alerts that already appeared once
        self.timer = QTimer(self)
        self.attitude_alert_once = False
        self.depth_alert_once = False
        self.ambient_temperature_alert_once = False
        self.ambient_pressure_alert_once = False
        self.internal_temperature_alert_once = False
        self.float_depth_alert_once = False

    def is_rov_connected(self):
        return self.rov_data_thread.connected

    def is_float_connected(self):
        return self.float_data_thread.connected

    def is_controller_connected(self):
        return self.get_controller_input() is not None

    def on_rov_data_sock_recv(self, payload_bytes):
        rov_data: ROVData = pickle.loads(payload_bytes)

        # Map all attributes in ROVData to their associated attributes in the DataInterface
        for attr in rov_data.__dict__:
            self.__setattr__(attr, rov_data.__getattribute__(attr))

        if not self.attitude_alert_once:
            if self.attitude.z > 4 or self.attitude.z < -5:
                self.attitude_alert.emit()
                self.attitude_alert_once = True
            else:
                pass
        if not self.depth_alert_once and (self.depth > 2.5 or self.depth < 1):
            self.depth_alert.emit()
            self.depth_alert_once = True

        if not self.ambient_temperature_alert_once and (
                self.ambient_temperature < 24 or self.ambient_temperature > 28):
            self.ambient_temperature_alert.emit()
            self.ambient_temperature_alert_once = True

        if not self.ambient_pressure_alert_once and self.ambient_pressure > 129:
            self.ambient_pressure_alert.emit()
            self.ambient_pressure_alert_once = True

        if not self.internal_temperature_alert_once and self.internal_temperature > 69:
            self.internal_temperature_alert.emit()
            self.internal_temperature_alert_once = True

        self.rov_data_update.emit()

    def on_float_data_sock_recv(self, payload_bytes):
        float_data: FloatData = pickle.loads(payload_bytes)

        # Map all attributes in ROVData to their associated attributes in the DataInterface
        for attr in float_data.__dict__:
            self.__setattr__(attr, float_data.__getattribute__(attr))

        self.float_data_update.emit()

        # Alert conditional popups
        if not self.float_depth_alert_once and (self.float_depth > 3 or self.float_depth < 1):
            self.float_depth_alert.emit()
            self.float_depth_alert_once = True

    def on_video_stream_sock_recv(self, payload_bytes, i):
        frame = pickle.loads(payload_bytes)
        height, width, channels = frame.shape
        self.camera_feeds[i] = QImage(frame, width, height, channels * width, QImage.Format.Format_BGR888)
        self.video_stream_update.emit(i)

    def f_stdout_ui_thread(self):
        while not self.app.closing:
            # Process redirected stdout
            self.redirect_stdout.flush()
            if self.redirect_stdout != sys.__stdout__:
                lines = self.redirect_stdout.getvalue().splitlines()
                for line in lines:
                    self.stdout_update.emit(StdoutType.UI, line)
                    print(line, file=sys.__stdout__)
                self.redirect_stdout.seek(0)
                self.redirect_stdout.truncate(0)

            # Process redirected stderr
            self.redirect_stderr.flush()
            if self.redirect_stderr != sys.__stderr__:
                lines = self.redirect_stderr.getvalue().splitlines()
                for line in lines:
                    self.stdout_update.emit(StdoutType.UI_ERROR, line)
                    print(line, file=sys.__stderr__)
                self.redirect_stderr.seek(0)
                self.redirect_stderr.truncate(0)

    def on_stdout_sock_recv(self, payload_bytes):
        source, line = pickle.loads(payload_bytes)
        self.stdout_update.emit(source, line)

    def get_controller_input(self):
        for event in pygame.event.get():
            if event.type == pygame.JOYDEVICEADDED:
                if self.joystick is None:
                    self.joystick = pygame.joystick.Joystick(0)
                    self.joystick.init()
                    print("Controller Connected", flush=True)
            elif event.type == pygame.JOYDEVICEREMOVED:
                self.joystick.quit()
                self.joystick = None
                print("Controller Disconnected", flush=True)
                return None
        if self.joystick is None:
            return None
        new_state = {
            "axes": [self.joystick.get_axis(i) for i in range(self.joystick.get_numaxes())],
            "buttons": [self.joystick.get_button(i) for i in range(self.joystick.get_numbuttons())],
            "hats": [self.joystick.get_hat(i) for i in range(self.joystick.get_numhats())]
        }
        return new_state

    def close(self):
        pygame.quit()
        self.rov_data_thread.join(10)
        self.stdout_sock_thread.join(10)
        self.stdout_ui_thread.join(10)
        self.controller_input_thread.join(10)
        for video_stream_thread in self.camera_threads:
            video_stream_thread.join(10)
