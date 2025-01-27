import io
import pickle
import sys
import time
from threading import Thread
import cv2
import numpy as np

from sock_stream_recv import SockStreamRecv
from sock_stream_send import SockStreamSend
from typing import TYPE_CHECKING, Sequence
import pygame

from PyQt6.QtCore import pyqtSignal, QObject, QTimer, Qt
from PyQt6.QtGui import QImage, QPainter, QPixmap

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

        self.redirect_stdout = redirect_stdout
        self.redirect_stderr = redirect_stderr

        self.attitude = Vector3(0, 0, 0)
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

        self.float_depth = 0

        self.camera_feeds = []
        self.camera_threads = []

        pygame.init()
        pygame.joystick.init()
        self.joystick = None

        self.overlay_enabled = True
        
        self.debug_print = True
        self.debug_angle = 0.0
        self.last_debug_time = time.time()

        self.current_frame_size = None

        self.attitude_center_pixmap = QPixmap("datainterface/attitudeCenter.png")
        self.attitude_lines_pixmap = QPixmap("datainterface/attitudeLines.png")

        def on_camera_feed_disconnect(i):
            self.camera_feeds[i] = None
            self.video_stream_update.emit(i)

        for i in range(self.camera_feed_count):
            self.camera_feeds.append(None)
            cam_thread = SockStreamRecv(self.app, ROV_IP, 52524 - i,
                                        lambda payload_bytes, j=i: self.on_video_stream_sock_recv(payload_bytes, j),
                                        lambda j=i: on_camera_feed_disconnect(j))
            self.camera_threads.append(cam_thread)
            cam_thread.start()

        self.rov_data_thread = SockStreamRecv(self.app, ROV_IP, 52525, self.on_rov_data_sock_recv,
                                              lambda: self.rov_data_update.emit())
        self.rov_data_thread.start()
        self.float_data_thread = SockStreamRecv(self.app, ROV_IP, 52625, self.on_float_data_sock_recv,
                                                lambda: self.float_data_update.emit())
        self.float_data_thread.start()

        self.stdout_ui_thread = Thread(target=self.f_stdout_ui_thread)
        self.stdout_ui_thread.start()

        self.stdout_sock_thread = SockStreamRecv(self.app, ROV_IP, 52535, self.on_stdout_sock_recv, None)
        self.stdout_sock_thread.start()

        self.controller_input_thread = SockStreamSend(self.app, ROV_IP, 52526, 0.01,
                                                      self.get_controller_input, None)
        self.controller_input_thread.start()

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
        for attr in rov_data.__dict__:
            setattr(self, attr, getattr(rov_data, attr))

        if not self.attitude_alert_once:
            if self.attitude.z > 4 or self.attitude.z < -5:
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

        self.rov_data_update.emit()

    def on_float_data_sock_recv(self, payload_bytes):
        float_data: FloatData = pickle.loads(payload_bytes)
        for attr in float_data.__dict__:
            setattr(self, attr, getattr(float_data, attr))
        self.float_data_update.emit()

        if not self.float_depth_alert_once and (self.float_depth > 3 or self.float_depth < 1):
            self.float_depth_alert.emit()
            self.float_depth_alert_once = True

    def on_video_stream_sock_recv(self, payload_bytes, i):
            if not payload_bytes:
                return

            frame = pickle.loads(payload_bytes)
            if frame is None or not isinstance(frame, np.ndarray):
                return

            start_time = time.time()

            height, width = frame.shape[:2]
            qimage = QImage(
                frame.data,
                width,
                height,
                frame.strides[0],
                QImage.Format.Format_BGR888
            )

            if i == 0 and self.overlay_enabled:
                #resize overlays if frame size changed
                if self.current_frame_size != (width, height):
                    self.current_frame_size = (width, height)
                    self.scaled_center_pixmap = self.attitude_center_pixmap.scaled(width, height)
                    self.scaled_lines_pixmap = self.attitude_lines_pixmap.scaled(width, height)

                #DEBUG PART
                if self.debug_print:
                    current_time = time.time()
                    elapsed = current_time - self.last_debug_time
                    self.last_debug_time = current_time
                    #change angle by 10 degrees per second * elapsed time
                    self.debug_angle += 10.0 * elapsed
                    self.debug_angle %= 360.0

                painter = QPainter(qimage)

                painter.drawPixmap(0, 0, self.scaled_center_pixmap)

                painter.save()
                painter.translate(width/2, height/2)

                #base rotation is self.attitude.z, add debug_angle if debug is on
                total_rotation = self.attitude.z
                if self.debug_print:
                    total_rotation += self.debug_angle

                painter.rotate(total_rotation)
                painter.translate(-width/2, -height/2)
                painter.drawPixmap(0, 0, self.scaled_lines_pixmap)
                painter.restore()

                painter.end()

            self.camera_feeds[i] = qimage
            self.video_stream_update.emit(i)

            if self.debug_print:
                total_processing_time = (time.time() - start_time) * 1000.0
                print(f"[UI] - Total frame processing time: {total_processing_time:.2f} ms")


    def f_stdout_ui_thread(self):
        while not self.app.closing:
            # Process redirected stdout
            self.redirect_stdout.flush()
            if self.redirect_stdout != sys.__stdout__:
                lines = self.redirect_stdout.getvalue().splitlines()
                for line in lines:
                    self.stdout_update.emit(StdoutType.UI, line)
                self.redirect_stdout.seek(0)
                self.redirect_stdout.truncate(0)

            # Process redirected stderr
            self.redirect_stderr.flush()
            if self.redirect_stderr != sys.__stderr__:
                lines = self.redirect_stderr.getvalue().splitlines()
                for line in lines:
                    self.stdout_update.emit(StdoutType.UI_ERROR, line)
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
        return {
            "axes": [self.joystick.get_axis(i) for i in range(self.joystick.get_numaxes())],
            "buttons": [self.joystick.get_button(i) for i in range(self.joystick.get_numbuttons())],
            "hats": [self.joystick.get_hat(i) for i in range(self.joystick.get_numhats())]
        }

    def close(self):
        pygame.quit()
        self.rov_data_thread.join(10)
        self.stdout_sock_thread.join(10)
        self.stdout_ui_thread.join(10)
        self.controller_input_thread.join(10)
        for video_stream_thread in self.camera_threads:
            video_stream_thread.join(10)
