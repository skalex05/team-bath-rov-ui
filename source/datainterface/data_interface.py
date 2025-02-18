import math
import pickle
import sys
import time
from threading import Thread
import cv2
import numpy as np

import cv2

from qt_sock_stream_recv import QSockStreamRecv
from sock_stream_send import SockStreamSend
from typing import TYPE_CHECKING, Sequence
from io import StringIO
import pygame

from PyQt6.QtCore import pyqtSignal, QObject, QTimer
from PyQt6.QtGui import QImage

from float_data import FloatData
from rov_data import ROVData
from vector3 import Vector3
from video_frame import VideoFrame
from stdout_type import StdoutType

if TYPE_CHECKING:
    from window import Window
    from app import App
    from numpy import ndarray

ROV_IP = "localhost"
FLOAT_IP = "localhost"


class DataInterface(QObject):
    rov_data_update = pyqtSignal()
    float_data_update = pyqtSignal()
    stdout_update = pyqtSignal(StdoutType, str)

    # ALERT SIGNALS
    attitude_alert = pyqtSignal()
    depth_alert = pyqtSignal()
    ambient_temperature_alert = pyqtSignal()
    ambient_pressure_alert = pyqtSignal()
    internal_temperature_alert = pyqtSignal()
    float_depth_alert = pyqtSignal()

    def __init__(self, app: "App", windows: Sequence["Window"], redirect_stdout: StringIO, redirect_stderr: StringIO):
        super().__init__()
        self.app: "App" = app
        self.windows: Sequence["Window"] = windows
        self.camera_feed_count: int = 3

        self.redirect_stdout = redirect_stdout
        self.redirect_stderr = redirect_stderr

        self.attitude = Vector3(0, 0, 0)  # Pitch, Yaw, Roll
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
        self.float_depth: float = 0

        # Camera Feeds

        self.camera_feeds: Sequence[VideoFrame] = []
        self.camera_threads: [QSockStreamRecv] = []

        # Controller State

        pygame.init()
        pygame.joystick.init()
        self.joystick = None

        self.debug_angle = 0.0
        self.last_debug_time = time.time()
        self.min_depth = 0.0
        self.max_depth = 5.0

        def on_camera_feed_disconnect(i):
            self.camera_feeds[i] = None
            self.video_stream_update.emit(i)

        # Video Receiver Threads
        for i in range(self.camera_feed_count):
            self.camera_feeds.append(VideoFrame())
            cam_thread = QSockStreamRecv(self.app, ROV_IP, 52524 - i,
                                         buffer_size=65536,
                                         protocol="udp")
            # Connect signals
            cam_thread.on_recv.connect(lambda payload_bytes, j=i: self.on_video_stream_sock_recv(payload_bytes, j))
            cam_thread.on_disconnect.connect(lambda j=i: self.on_camera_feed_disconnect(j))
            self.camera_threads.append(cam_thread)
            cam_thread.start()

        # ROV Data Thread
        self.rov_data_thread = QSockStreamRecv(self.app, ROV_IP, 52525)
        self.rov_data_thread.on_recv.connect(self.on_rov_data_sock_recv)
        self.rov_data_thread.start()

        # ROV Float Thread
        self.float_data_thread = QSockStreamRecv(self.app, ROV_IP, 52625)
        self.float_data_thread.on_recv.connect(self.on_float_data_sock_recv)
        self.float_data_thread.start()

        # STDOUT UI Thread
        # This thread processes redirected stdout to be displayed in the UI and in console
        self.stdout_ui_thread = Thread(target=self.f_stdout_ui_thread)
        self.stdout_ui_thread.start()

        # STDOUT Socket Thread
        # This thread processes stdout that has been received across a socket
        self.stdout_sock_thread = QSockStreamRecv(self.app, ROV_IP, 52535)
        self.stdout_sock_thread.on_recv.connect(self.on_stdout_sock_recv)
        self.stdout_sock_thread.start()

        # Controller Input Thread
        # Collects and sends input to the ROV
        self.controller_input_thread = SockStreamSend(self.app, ROV_IP, 52526, 0.01,
                                                      self.get_controller_input)
        self.controller_input_thread.start()

        self.timer = QTimer(self)
        self.attitude_alert_once = False
        self.depth_alert_once = False
        self.ambient_temperature_alert_once = False
        self.ambient_pressure_alert_once = False
        self.internal_temperature_alert_once = False
        self.float_depth_alert_once = False

    def on_camera_feed_disconnect(self, i) -> None:
        # Wait until the VideoFrame is not being accessed before overwriting the frame
        with self.camera_feeds[i].lock:
            self.camera_feeds[i].frame = None
            self.camera_feeds[i].new_frame.emit()

    def is_rov_connected(self) -> bool:
        return self.rov_data_thread.is_connected()

    def is_float_connected(self) -> bool:
        return self.float_data_thread.is_connected()

    def is_controller_connected(self) -> bool:
        return self.get_controller_input() is not None

    def on_rov_data_sock_recv(self, payload_bytes) -> None:
        rov_data: ROVData = pickle.loads(payload_bytes)
        for attr in rov_data.__dict__:
            setattr(self, attr, getattr(rov_data, attr))

        if not self.attitude_alert_once and (self.attitude.z > 4 or self.attitude.z < -5):
            self.attitude_alert_once = True
            self.attitude_alert.emit()

        if not self.depth_alert_once and (self.depth > 2.5 or self.depth < 1):
            self.depth_alert_once = True
            self.depth_alert.emit()

        if not self.ambient_temperature_alert_once and (
                self.ambient_temperature < 24 or self.ambient_temperature > 28):
            self.ambient_temperature_alert_once = True
            self.ambient_temperature_alert.emit()

        if not self.ambient_pressure_alert_once and self.ambient_pressure > 129:
            self.ambient_pressure_alert_once = True
            self.ambient_pressure_alert.emit()

        if not self.internal_temperature_alert_once and self.internal_temperature > 69:
            self.internal_temperature_alert_once = True
            self.internal_temperature_alert.emit()

        self.rov_data_update.emit()
        
    def on_float_data_sock_recv(self, payload_bytes: bytes) -> None:
        float_data: FloatData = pickle.loads(payload_bytes)
        for attr in float_data.__dict__:
            setattr(self, attr, getattr(float_data, attr))
        self.float_data_update.emit()

        if not self.float_depth_alert_once and (self.float_depth > 3 or self.float_depth < 1):
            self.float_depth_alert_once = True
            self.float_depth_alert.emit()

    def on_video_stream_sock_recv(self, payload: bytes, i: int) -> None:
        # Process the raw video bytes received
        encoded: ndarray = pickle.loads(payload)
        if encoded is None:
            self.on_camera_feed_disconnect(i)
            return

        # Decode the frame back into a numpy pixel array
        frame = cv2.imdecode(encoded, 1)
        h, w, _ = frame.shape

        # Generate the new QImage for the feed
        frame = QImage(frame, w, h, QImage.Format.Format_BGR888)

        #  Wait until no other threads are accessing the VideoFrame
        with self.camera_feeds[i].lock:
            self.camera_feeds[i].frame = frame
            self.camera_feeds[i].new_frame.emit()

    def f_stdout_ui_thread(self) -> None:
        while not self.app.closing:
            time.sleep(0)
            # Process redirected stdout
            self.redirect_stdout.flush()
            for redirect, source, type_ in ((self.redirect_stdout, sys.__stdout__, StdoutType.UI),
                                            (self.redirect_stderr, sys.__stderr__, StdoutType.UI_ERROR)):
                # If stdout has been redirected, send it to redirected and source location
                if redirect != source:
                    lines = redirect.getvalue().splitlines()
                    for line in lines:
                        self.stdout_update.emit(type_, line)
                        print(line, file=source)
                    # Clean up redirect buffer
                    redirect.seek(0)
                    redirect.truncate(0)

    def on_stdout_sock_recv(self, payload_bytes: bytes) -> None:
        # Receive stdout from socket
        try:
            msg: tuple[StdoutType, str] = pickle.loads(payload_bytes)
            source, line = msg
            self.stdout_update.emit(source, line)
            print(f"[{source.name}] {line}", file=sys.__stdout__)
        except ValueError:
            print("Received stdout was not of format <STDOUTTYPE>, <str>", file=sys.stderr)

    def get_controller_input(self) -> bytes:
        # Process all pygame events since the function was last called
        for event in pygame.event.get():
            # Handle Controller connection and disconnection
            if event.type == pygame.JOYDEVICEADDED:
                if self.joystick is None:
                    self.joystick = pygame.joystick.Joystick(0)
                    self.joystick.init()
                    print("Controller Connected", flush=True)
            elif event.type == pygame.JOYDEVICEREMOVED:
                self.joystick.quit()
                self.joystick = None
                print("Controller Disconnected", flush=True)
                return pickle.dumps(None)
        if self.joystick is None:
            return pickle.dumps(None)
        new_state = {
            "axes": [self.joystick.get_axis(i) for i in range(self.joystick.get_numaxes())],
            "buttons": [self.joystick.get_button(i) for i in range(self.joystick.get_numbuttons())],
            "hats": [self.joystick.get_hat(i) for i in range(self.joystick.get_numhats())]
        }
        return pickle.dumps(new_state)

    def close(self):
        if not self.app.closing:
            raise AssertionError("This function should only be called from App after App.closing is set to True")
        # Rejoin all threads
        pygame.quit()
        print("Joining ROV data thread", file=sys.__stdout__, flush=True)
        self.rov_data_thread.wait(10)
        print("Joining socket stdout thread", file=sys.__stdout__, flush=True)
        self.stdout_sock_thread.wait(10)
        print("Joining ui stdout thread", file=sys.__stdout__, flush=True)
        self.stdout_ui_thread.join(10)
        print("Joining controller thread", file=sys.__stdout__, flush=True)
        self.controller_input_thread.join(10)
        print("Joining video stream threads", file=sys.__stdout__, flush=True)
        for video_stream_thread in self.camera_threads:
            video_stream_thread.wait(10)
        print("Data Interface closed successfully", file=sys.__stdout__, flush=True)

