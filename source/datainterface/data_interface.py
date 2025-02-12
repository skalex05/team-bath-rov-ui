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

from PyQt6.QtCore import pyqtSignal, QObject, QTimer, Qt
from PyQt6.QtGui import QImage, QPainter, QPixmap

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

        # MATE FLOAT Data
        self.float_depth: float = 0

        # Camera Feeds

        self.camera_feeds: Sequence[VideoFrame] = []
        self.camera_threads: [QSockStreamRecv] = []

        # Controller State

        pygame.init()
        pygame.joystick.init()
        self.joystick = None

        self.overlay_enabled = True
        self.debug_print = False
        self.debug_angle = 0.0
        self.last_debug_time = time.time()
        self.min_depth = 0.0
        self.max_depth = 5.0

        self.attitude_center_pixmap = QPixmap("datainterface/attitudeCenter.png")
        self.attitude_lines_pixmap = QPixmap("datainterface/attitudeLines.png")

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
        frame = self.overlay_pitch_yaw(frame)
        frame = self.overlay_depth(frame)
        h, w, _ = frame.shape
        # Wait until no other threads are accessing the VideoFrame

        # Generate the new QImage for the feed
        frame = QImage(frame, w, h, QImage.Format.Format_BGR888)
        if i == 0 and self.overlay_enabled:
            # resize overlays if frame size changed

            scaled_center_pixmap = self.attitude_center_pixmap.scaled(w, h)
            scaled_lines_pixmap = self.attitude_lines_pixmap.scaled(w, h)

            painter = QPainter(frame)

            painter.drawPixmap(0, 0, scaled_center_pixmap)

            painter.save()
            painter.translate(w / 2, h / 2)

            # base rotation is self.attitude.z, add debug_angle if debug is on
            total_rotation = self.attitude.z

            painter.rotate(total_rotation)
            painter.translate(-w / 2, -h / 2)
            painter.drawPixmap(0, 0, scaled_lines_pixmap)
            painter.restore()

            painter.end()

        with self.camera_feeds[i].lock:
            # Generate the new QImage for the feed
            frame = QImage(frame, w, h, QImage.Format.Format_BGR888)
            if i == 0 and self.overlay_enabled:
                #resize overlays if frame size changed
                if self.current_frame_size != (w, h):
                    self.current_frame_size = (w, h)
                    self.scaled_center_pixmap = self.attitude_center_pixmap.scaled(w, h)
                    self.scaled_lines_pixmap = self.attitude_lines_pixmap.scaled(w, h)

                #DEBUG PART
                if self.debug_print:
                    current_time = time.time()
                    elapsed = current_time - self.last_debug_time
                    self.last_debug_time = current_time
                    #change angle by 10 degrees per second * elapsed time
                    self.debug_angle += 10.0 * elapsed
                    self.debug_angle %= 360.0

                painter = QPainter(frame)
                painter.drawPixmap(0, 0, self.scaled_center_pixmap)

                painter.save()
                painter.translate(w/2, h/2)

                #base rotation is self.attitude.z, add debug_angle if debug is on
                total_rotation = self.attitude.z
                if self.debug_print:
                    total_rotation += self.debug_angle

                painter.rotate(total_rotation)
                painter.translate(0,(self.attitude.x % 360 -180 ) / 180 * (h/2))
                painter.translate(-w/2, -h/2)
                painter.drawPixmap(0, 0, self.scaled_lines_pixmap)
                painter.restore()

                painter.end()
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

    def overlay_depth(self, frame):
        depth_value = self.depth 
        #text
        font = cv2.FONT_HERSHEY_SIMPLEX
        font_scale = 0.5
        text_color = (255, 255, 255) 
        thickness = 1
        height, width = frame.shape[:2]
        #Display text
        depth_text = f"Depth: {depth_value:.2f} m"
        text_size = cv2.getTextSize(depth_text, font, font_scale, thickness)[0]
        text_x = width - text_size[0] - 10 
        text_y = height - 10 
        cv2.putText(frame, depth_text, (text_x, text_y), font, font_scale, text_color, thickness, cv2.LINE_AA)
        #Indicator
        indicator_start = (width - 50, height - 110) 
        indicator_end = (width - 50, height - 40) 
        cv2.rectangle(frame, indicator_start, indicator_end, (50, 50, 50), 25)  
        cv2.putText(frame, f"{self.min_depth:.1f}m", (indicator_start[0] - 60, indicator_end[1]), font, font_scale, text_color, thickness, cv2.LINE_AA)
        cv2.putText(frame, f"{self.max_depth:.1f}m", (indicator_start[0] - 60, indicator_start[1]), font, font_scale, text_color, thickness, cv2.LINE_AA)
        cv2.putText(frame, f"{self.min_depth:.1f}m", (indicator_start[0] - 30, indicator_end[1]), font, font_scale, text_color, thickness, cv2.LINE_AA)
        cv2.putText(frame, f"{self.max_depth:.1f}m", (indicator_start[0] - 30, indicator_start[1]), font, font_scale, text_color, thickness, cv2.LINE_AA)
        # # Draw arrow on the indicator 
        if self.min_depth <= depth_value <= self.max_depth:
            normalized_depth = (depth_value - self.min_depth) / (self.max_depth - self.min_depth)
            arrow_y = int(indicator_end[1] + (indicator_start[1] - indicator_end[1]) * normalized_depth)
            arrow_x = indicator_start[0] + 20
            cv2.arrowedLine(frame, (arrow_x+10, arrow_y), (arrow_x, arrow_y), (255, 255, 255), 2, tipLength=1.2)
            cv2.rectangle(frame, (width - 50, arrow_y), indicator_end, (180, 160, 160), 25)   
            
        return frame
    
    def overlay_pitch_yaw(self, frame):
        pitch_value = self.attitude.x 
        yaw_value = self.attitude.y   
        # Text
        font = cv2.FONT_HERSHEY_SIMPLEX
        font_scale = 0.4
        color = (255, 255, 255) 
        thickness = 2
        height, width = frame.shape[:2]
        center_x = width // 2
        center_y = height // 2 + 30
        #Off center values
        pitch_position = (center_x - 70, center_y) 
        roll_position = (center_x + 40, center_y) 
        cv2.putText(frame, f"{pitch_value:.1f}", pitch_position, font, font_scale, color, thickness, cv2.LINE_AA)
        cv2.putText(frame, f"{yaw_value:.1f}", roll_position, font, font_scale, color, thickness, cv2.LINE_AA)
        return frame