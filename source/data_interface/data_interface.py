import io
import pickle
import struct
import sys
import traceback
from collections.abc import Sequence
from socket import socket, AF_INET, SOCK_DGRAM, SOCK_STREAM
from threading import Thread
from typing import TYPE_CHECKING
import time
import pygame

from PyQt6.QtCore import pyqtSignal, QObject
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

        self.camera_feeds = []
        self.camera_threads: [Thread] = []

        # Controller State

        self.controller_state = None

        # Start Threads

        for i in range(self.camera_feed_count):
            self.camera_feeds.append(None)
            cam_thread = Thread(target=self.f_video_stream_thread, args=(i,))
            self.camera_threads.append(cam_thread)
            cam_thread.start()

        self.rov_data_thread = Thread(target=self.f_rov_data_thread)
        self.rov_data_thread.start()

        self.float_data_thread = Thread(target=self.f_float_data_thread)
        self.float_data_thread.start()

        self.stdout_thread = Thread(target=self.f_stdout_thread)
        self.stdout_thread.start()


        self.controller_input_thread = Thread(target=self.f_controller_input_thread)
        self.controller_input_thread.start()

        # Alerts that already appeared once
        self.attitude_alert_once = False
        self.depth_alert_once = False
        self.ambient_temperature_alert_once = False
        self.ambient_pressure_alert_once = False
        self.internal_temperature_alert_once = False
        self.float_depth_alert_once = False

    def f_rov_data_thread(self):
        data_server = socket(AF_INET, SOCK_DGRAM)
        data_server.bind((ROV_IP, 52525))
        data_server.setblocking(False)
        data_server.settimeout(2)
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

            # Alert conditional popups
            if not self.attitude_alert_once and ((self.attitude.x > 45 or self.attitude.x < -45) or
                                                 (self.attitude.y > 360 or self.attitude.y < 0) or
                                                 (self.attitude.x > 5 or self.attitude.x < -5)):
                self.attitude_alert.emit()
                self.attitude_alert_once = True

            if not self.depth_alert_once and (self.depth > 2.5 or self.depth < 1):
                self.depth_alert.emit()
                self.depth_alert_once = True

            if not self.ambient_temperature_alert_once and (self.ambient_temperature < 24 or self.ambient_temperature > 28):
                self.ambient_temperature_alert.emit()
                self.ambient_temperature_alert_once = True

            if not self.ambient_pressure_alert_once and self.ambient_pressure > 129:
                self.ambient_pressure_alert.emit()
                self.ambient_pressure_alert_once = True

            if not self.internal_temperature_alert_once and self.internal_temperature > 69:
                self.internal_temperature_alert.emit()
                self.internal_temperature_alert_once = True

            time.sleep(0.0167)

    def f_float_data_thread(self):
        data_server = socket(AF_INET, SOCK_DGRAM)
        data_server.bind((FLOAT_IP, 52625))
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
        time.sleep(0.01)

            # Alert conditional popups
            if not self.float_depth_alert_once and (self.float_depth > 3 or self.float_depth < 1):
                self.float_depth_alert.emit()
                self.float_depth_alert_once = True

    def f_video_stream_thread(self, i):
        video_server = socket(AF_INET, SOCK_STREAM)
        video_server.bind((ROV_IP, 52524 - i))
        video_server.settimeout(2)
        self.video_stream_update.emit(i)

        def handshake():
            while not self.app.closing:
                try:
                    # Handshake frame size
                    video_server.listen()
                    con, addr = video_server.accept()
                    size = con.recv(8)
                    size = struct.unpack("Q", size)[0]
                    pack = struct.pack("Q", size)
                    con.send(pack)
                    print(f"Camera {i + 1} Connected")
                    return con, size
                except TimeoutError:
                    pass
            return None, None

        conn, frame_size = handshake()
        data = b""
        while not self.app.closing:
            # Get frame
            try:
                while len(data) < frame_size:
                    data += conn.recv(4096)

                frame = data[:frame_size]
                data = data[frame_size:]
                frame = pickle.loads(frame)
                height, width, channels = frame.shape
                self.camera_feeds[i] = QImage(frame, width, height, channels * width, QImage.Format.Format_BGR888)
                self.video_stream_update.emit(i)
            except ConnectionError:
                self.camera_feeds[i] = None
                self.video_stream_update.emit(i)
                conn, frame_size = handshake()
            except TimeoutError:
                pass

    def f_stdout_thread(self):
        stdout_server = socket(AF_INET, SOCK_STREAM)
        stdout_server.bind((ROV_IP, 52535))
        stdout_server.settimeout(0.5)

        conn, _ = None, None
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

            try:
                try:
                    if conn is None:
                        raise ConnectionError()
                    source, line = pickle.loads(conn.recv(1024))
                    self.stdout_update.emit(source, line)
                except ConnectionError:
                    stdout_server.listen()
                    conn, _ = stdout_server.accept()
            except TimeoutError:
                pass
            except Exception as e:
                print(e, file=self.redirect_stderr)
            time.sleep(0.0167)

    def f_controller_input_thread(self):
        input_client = None

        pygame.init()

        joystick = None

        while not self.app.closing:
            time.sleep(0.01)
            for event in pygame.event.get():
                if event.type == pygame.JOYDEVICEADDED:
                    pygame.joystick.init()
                    joystick = pygame.joystick.Joystick(0)
                    joystick.init()
                elif event.type == pygame.JOYDEVICEREMOVED:
                    joystick.quit()
                    joystick = None

            if joystick is None:
                continue

            if input_client is None:
                try:
                    input_client = socket(AF_INET, SOCK_STREAM)
                    input_client.connect(("localhost", 52526))
                except ConnectionError:
                    input_client = None
                    continue

            try:
                new_state = {
                    "axes": [joystick.get_axis(i) for i in range(joystick.get_numaxes())],
                    "buttons": [joystick.get_button(i) for i in range(joystick.get_numbuttons())],
                    "hats": [joystick.get_hat(i) for i in range(joystick.get_numhats())]
                }
                print(new_state)
                if self.controller_state == new_state:
                    continue

                try:
                    self.controller_state = new_state
                    payload = pickle.dumps((self.controller_state, time.time()))
                    input_client.send(payload)
                except ConnectionError as e:
                    print("ERR", e)

                time.sleep(0.01)
            except Exception as e:
                print(traceback.format_exc(e))

        pygame.quit()

    def close(self):
        self.rov_data_thread.join(10)
        self.stdout_thread.join(10)
        for video_stream_thread in self.camera_threads:
            video_stream_thread.join(10)
