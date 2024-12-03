import os
import subprocess
import time

from PyQt6.QtWidgets import QLabel, QRadioButton, QWidget, QPlainTextEdit, QPushButton, QProgressBar, QScrollArea, \
    QMessageBox

from PyQt6.QtCore import QRect, QTimer

from datainterface.data_interface import DataInterface, StdoutType, ROV_IP, FLOAT_IP
from action_thread import ActionThread
from datainterface.action_enum import ActionEnum
from datainterface.sock_stream_send import SockSend
from datainterface.video_stream import VideoStream
from window import Window

path_dir = os.path.dirname(os.path.realpath(__file__))

# Timer prerequisites
DURATION_INT = 900


class Copilot(Window):
    def __init__(self, *args):
        super().__init__(os.path.join(path_dir, "copilot.ui"), *args)

        # Appearance

        self.v_pad = 5
        self.v_dp = 2

        self.data: DataInterface | None = None

        # Sensor Data

        self.rov_attitude_value: QLabel = self.findChild(QLabel, "ROVAttitudeValue")
        self.rov_angular_accel_value: QLabel = self.findChild(QLabel, "ROVAngularAccelerationValue")
        self.rov_angular_velocity_value: QLabel = self.findChild(QLabel, "ROVAngularVelocityValue")
        self.rov_acceleration_value: QLabel = self.findChild(QLabel, "ROVAccelerationValue")
        self.rov_velocity_value: QLabel = self.findChild(QLabel, "ROVVelocityValue")

        self.rov_depth_value: QLabel = self.findChild(QLabel, "ROVDepthValue")
        self.ambient_water_temp_value: QLabel = self.findChild(QLabel, "AmbientWaterTempValue")
        self.ambient_pressure_value: QLabel = self.findChild(QLabel, "AmbientPressureValue")
        self.internal_temp_value: QLabel = self.findChild(QLabel, "InternalTempValue")

        self.actuator1_value: QLabel = self.findChild(QLabel, "Actuator1Value")
        self.actuator2_value: QLabel = self.findChild(QLabel, "Actuator2Value")
        self.actuator3_value: QLabel = self.findChild(QLabel, "Actuator3Value")
        self.actuator4_value: QLabel = self.findChild(QLabel, "Actuator4Value")
        self.actuator5_value: QLabel = self.findChild(QLabel, "Actuator5Value")
        self.actuator6_value: QLabel = self.findChild(QLabel, "Actuator6Value")

        self.float_depth_value: QLabel = self.findChild(QLabel, "MATEFloatDepthValue")

        # Timer

        self.time_left_int = DURATION_INT

        self.startTimeButton = self.findChild(QPushButton, "startTimeButton")
        self.startTimeButton.clicked.connect(self.start_timer)
        self.stop_time_button = self.findChild(QPushButton, "stopTimeButton")
        self.stop_time_button.clicked.connect(self.stop_timer)
        self.remainingTime = self.findChild(QLabel, "remainingTime")

        self.update_time()

        self.progressTimeBar = self.findChild(QProgressBar, "progressTimeBar")
        self.progressTimeBar.setMinimum(0)
        self.progressTimeBar.setMaximum(DURATION_INT)

        # Actions

        self.recalibrate_imu_action: QRadioButton = self.findChild(QRadioButton, "RecalibrateIMUAction")
        self.recalibrate_imu_action_thread = ActionThread(self.recalibrate_imu_action,
                                                          self.recalibrate_imu)

        self.rov_power_action: QRadioButton = self.findChild(QRadioButton, "ROVPowerAction")
        self.rov_power_action_thread = ActionThread(self.rov_power_action, retain_state=True,
                                                    target=self.on_rov_power)

        self.maintain_depth_action: QRadioButton = self.findChild(QRadioButton, "MaintainDepthAction")
        self.maintain_depth_action_thread = ActionThread(self.maintain_depth_action, retain_state=True,
                                                         target=self.maintain_depth)

        self.reinitialise_cameras_action: QRadioButton = self.findChild(QRadioButton, "ReinitialiseCameras")
        self.reinitialise_cameras_action_thread = ActionThread(self.reinitialise_cameras_action, retain_state=True,
                                                               target=self.reinitialise_cameras)

        self.connect_float_action: QRadioButton = self.findChild(QRadioButton, "ConnectFloatAction")
        self.connect_float_action_thread = ActionThread(self.connect_float_action, retain_state=True,
                                                        target=self.connect_float)

        self.reset_alerts_action: QRadioButton = self.findChild(QRadioButton, "ResetAlerts")
        self.reset_alerts_action_thread = ActionThread(self.reset_alerts_action, self.reset_alerts)

        self.main_cam: QLabel = self.findChild(QLabel, "MainCameraView")

        # Stdout

        self.stdout_window: QPlainTextEdit = self.findChild(QPlainTextEdit, "Stdout")
        self.stdout_cursor = self.stdout_window.textCursor()

        # Tasks

        self.task_list: QScrollArea = self.findChild(QScrollArea, "TaskList")
        self.task_list_contents: QWidget = self.task_list.findChild(QWidget, "TaskListContents")
        self.build_task_widgets()

    def attach_data_interface(self):
        self.data = self.app.data_interface
        self.data.rov_data_update.connect(self.update_rov_data)
        self.data.float_data_update.connect(self.update_float_data)
        self.data.video_stream_update.connect(self.update_video)
        self.data.stdout_update.connect(self.update_stdout)

        # Alert connect
        self.data.attitude_alert.connect(self.alert_attitude)
        self.data.depth_alert.connect(self.alert_depth)
        self.data.ambient_pressure_alert.connect(self.alert_ambient_pressure)
        self.data.ambient_temperature_alert.connect(self.alert_ambient_temperature)
        self.data.internal_temperature_alert.connect(self.alert_internal_temperature)
        self.data.float_depth_alert.connect(self.alert_float_depth)

    # Timer Functions

    @staticmethod
    def secs_to_minsec(secs: int):
        mins = secs // 60
        secs = secs % 60
        minsec = f'{mins:02}:{secs:02}'
        return minsec

    def start_timer(self):
        if not self.data.timer.isActive():
            try:
                self.data.timer.timeout.disconnect(self.timer_timeout)
            except TypeError:
                pass

            self.data.timer.timeout.connect(self.timer_timeout)
            self.data.timer.setInterval(1000)
            self.data.timer.start()
            self.stop_time_button.setText("Stop")

    def stop_timer(self):
        if not self.data.timer.isActive():
            # If the timer is inactive, reset the timer
            self.time_left_int = DURATION_INT
            self.app.reset_task_completion()
            self.update_time()
        self.data.timer.stop()
        self.stop_time_button.setText("Reset")

    def timer_timeout(self):
        self.time_left_int -= 1

        if self.time_left_int == 0:
            self.stop_timer()

        self.update_time()

    def update_time(self):
        minsec = Copilot.secs_to_minsec(self.time_left_int)
        self.remainingTime.setText(minsec)
        self.progressTimeBar.setValue(DURATION_INT - self.time_left_int)

    def build_task_widgets(self):
        list_geometry = self.task_list_contents.geometry()
        list_geometry.setHeight(len(self.app.tasks) * self.app.tasks[0].height())
        self.task_list_contents.setGeometry(list_geometry)
        # Sort display order of tasks into chronological order
        # Set the parents of each task widget to be the list container
        # Move the task to fit at the correct position in the list
        for i, task in enumerate(self.app.tasks):
            task.setParent(self.task_list_contents)
            geometry = QRect(0, i * task.height(), list_geometry.width(), task.height())
            task.setGeometry(geometry)

    # Action Functions
    def recalibrate_imu(self):
        print("Recalibrating...")
        time.sleep(3)
        print("Recalibrated IMU!")

    def on_rov_power(self):
        if self.rov_power_action.isChecked():
            print("Powering On!")
            self.rov_power_action.setChecked(False)
            if os.name == "nt":
                ex = "python.exe"
            else:
                ex = "python3"
            self.app.rov_data_source_proc = subprocess.Popen([ex, "datainterface//rov_dummy.py"])
            print("Power On!")
            self.rov_power_action.setChecked(True)
        else:
            self.rov_power_action.setChecked(True)
            print("Powering Off!")
            self.app.rov_data_source_proc.terminate()
            self.app.rov_data_source_proc = None
            self.rov_power_action.setChecked(False)
            if self.maintain_depth_action.isChecked():
                self.maintain_depth_action.setChecked(False)
                self.maintain_depth()

            print("Power Off!")

    def maintain_depth(self):
        depth = self.data.depth
        if self.data.is_rov_connected():
            SockSend(self.app, ROV_IP, 52527, (ActionEnum.MAINTAIN_ROV_DEPTH,
                                               self.maintain_depth_action.isChecked(), depth))
        if self.maintain_depth_action.isChecked() and self.data.is_rov_connected():
            self.maintain_depth_action.setText(f"Maintaining Depth ({depth} m)")
            print(f"Maintaining depth of {depth} m")
        else:
            self.maintain_depth_action.setText("Maintain Depth")
            if self.data.is_rov_connected():
                print("No longer maintaining depth")
            else:
                self.maintain_depth_action.setChecked(False)

    def reinitialise_cameras(self):
        # Check cameras aren't already being initialised
        if self.data.is_rov_connected():
            SockSend(self.app, ROV_IP, 52527, ActionEnum.REINIT_CAMS)
        time.sleep(1)
        self.reinitialise_cameras_action.setChecked(False)

    def reset_alerts(self):
        self.data.attitude_alert_once = False
        self.data.depth_alert_once = False
        self.data.ambient_temperature_alert_once = False
        self.data.ambient_pressure_alert_once = False
        self.data.internal_temperature_alert_once = False
        self.data.float_depth_alert_once = False
        # Uncheck button trick
        self.reset_alerts_action.setAutoExclusive(False)
        self.reset_alerts_action.setChecked(False)
        self.reset_alerts_action.setAutoExclusive(True)

    def connect_float(self):
        if self.connect_float_action.isChecked():
            self.connect_float_action.setChecked(False)
            try:
                self.app.float_data_source_proc = subprocess.Popen(
                    ["python.exe", "datainterface//float_data_source.py"])
            except FileNotFoundError:
                self.app.float_data_source_proc = subprocess.Popen(["python3", "datainterface//float_data_source.py"])
            print("Connecting...")
            time.sleep(2)
            print("Connected!")
            self.connect_float_action.setChecked(True)
            self.connect_float_action.setText("Disconnect Float")
        else:
            self.connect_float_action.setChecked(True)
            print("Disconnecting...")
            self.app.float_data_source_proc.terminate()
            self.app.float_data_source_proc = None
            time.sleep(2)
            print("Disconnected!")
            self.connect_float_action.setChecked(False)
            self.connect_float_action.setText("Connect Float")

    def update_stdout(self, source, line):
        # Display latest data for window
        if source == StdoutType.UI:
            line = "[UI] - " + line
        elif source == StdoutType.UI_ERROR:
            line = "[UI ERR] - " + line
        elif source == StdoutType.ROV:
            line = "[ROV] - " + line
        elif source == StdoutType.ROV_ERROR:
            line = "[ROV ERR] - " + line

        self.stdout_window.appendPlainText(line)

        # Scroll to bottom if scrollbar is less than 5 from bottom
        if self.stdout_window.verticalScrollBar().maximum() - self.stdout_window.verticalScrollBar().value() < 5:
            self.stdout_window.ensureCursorVisible()

    def update_rov_data(self):
        if self.data.is_rov_connected():
            t = self.data.attitude
            self.rov_attitude_value.setText(
                f"{t.x:<{self.v_pad}.{self.v_dp}f}°, {t.y:<{self.v_pad}.{self.v_dp}f}°, {t.z:<{self.v_pad}.{self.v_dp}f}°")
            t = self.data.angular_acceleration
            self.rov_angular_accel_value.setText(
                f"{t.x:<{self.v_pad}.{self.v_dp}f}, {t.y:<{self.v_pad}.{self.v_dp}f}, {t.z:<{self.v_pad}.{self.v_dp}f} m/s")
            t = self.data.angular_velocity
            self.rov_angular_velocity_value.setText(
                f"{t.x:<{self.v_pad}.{self.v_dp}f}, {t.y:<{self.v_pad}.{self.v_dp}f}, {t.z:<{self.v_pad}.{self.v_dp}f} m/s")
            t = self.data.acceleration
            self.rov_acceleration_value.setText(
                f"{t.x:<{self.v_pad}.{self.v_dp}f}, {t.y:<{self.v_pad}.{self.v_dp}f}, {t.z:<{self.v_pad}.{self.v_dp}f} m/s")
            t = self.data.velocity
            self.rov_velocity_value.setText(
                f"{t.x:<{self.v_pad}.{self.v_dp}f}, {t.y:<{self.v_pad}.{self.v_dp}f}, {t.z:<{self.v_pad}.{self.v_dp}f} m/s")

            self.rov_depth_value.setText(f"{self.data.depth:<{self.v_pad}.{self.v_dp}f} m")
            self.ambient_water_temp_value.setText(f"{self.data.ambient_temperature:<{self.v_pad}.{self.v_dp}f}°C")
            self.ambient_pressure_value.setText(f"{self.data.ambient_pressure:<{self.v_pad}.{self.v_dp}f} KPa")
            self.internal_temp_value.setText(f"{self.data.internal_temperature:<{self.v_pad}.{self.v_dp}f} °C")

            self.actuator1_value.setText(f"{int(self.data.actuator_1):>3} %")
            self.actuator2_value.setText(f"{int(self.data.actuator_2):>3} %")
            self.actuator3_value.setText(f"{int(self.data.actuator_3):>3} %")
            self.actuator4_value.setText(f"{int(self.data.actuator_4):>3} %")
            self.actuator5_value.setText(f"{int(self.data.actuator_5):>3} %")
            self.actuator6_value.setText(f"{int(self.data.actuator_6):>3} %")

        else:
            for label in [self.rov_attitude_value, self.rov_angular_accel_value, self.rov_angular_velocity_value,
                          self.rov_acceleration_value, self.rov_velocity_value, self.rov_depth_value,
                          self.ambient_pressure_value, self.ambient_water_temp_value, self.internal_temp_value,
                          self.actuator1_value, self.actuator2_value, self.actuator3_value,
                          self.actuator4_value, self.actuator5_value, self.actuator6_value]:
                label.setText("ROV Disconnected")

        if not self.maintain_depth_action.isChecked():
            self.maintain_depth_action.setText("Maintain Depth")

    def update_float_data(self):
        if self.data.is_float_connected():
            self.float_depth_value.setText(f"{self.data.float_depth} m")
        else:
            self.float_depth_value.setText("Float Disconnected")

    def update_video(self, i: int):
        if i != 0:
            return
        try:
            frame = self.data.camera_feeds[0]
            if frame:
                rect = self.main_cam.geometry()
                self.main_cam.setPixmap(VideoStream.generate_pixmap(frame, rect.width(), rect.height()))
            else:
                raise IndexError()
        except IndexError:
            self.main_cam.setText("Main Camera Disconnected")

        self.update()

    # Alert messages, need upgrade
    def alert_attitude(self):
        print("Warning!", f"{'Roll is: '}{self.data.attitude.z}")
        QMessageBox.warning(self, "Warning", f"{'Roll is: '}{self.data.attitude.z}")
        self.attitude_alert_timer = QTimer(self)
        self.attitude_alert_timer.timeout.connect(self.attitude_alert_once_timeout)
        self.attitude_alert_timer.start(20000)

    def alert_depth(self):
        print("Warning!", f"{'Depth is: '}{self.data.depth}")
        QMessageBox.warning(self, "Warning", f"{'Depth is: '}{self.data.depth}")
        self.depth_alert_timer = QTimer(self)
        self.depth_alert_timer.timeout.connect(self.depth_alert_once_timeout)
        self.depth_alert_timer.start(20000)

    def alert_ambient_pressure(self):
        print("Warning!", f"{'Ambient pressure is: '}{self.data.ambient_pressure}")
        QMessageBox.warning(self, "Warning", f"{'Ambient pressure is: '}{self.data.ambient_pressure}")
        self.ambient_pressure_alert_timer = QTimer(self)
        self.ambient_pressure_alert_timer.timeout.connect(self.ambient_pressure_alert_once_timeout)
        self.ambient_pressure_alert_timer.start(20000)

    def alert_ambient_temperature(self):
        print("Warning!", f"{'Ambient temperature is: '}{self.data.ambient_temperature}")
        QMessageBox.warning(self, "Warning", f"{'Ambient temperature is: '}{self.data.ambient_temperature}")
        self.ambient_temperature_alert_timer = QTimer(self)
        self.ambient_temperature_alert_timer.timeout.connect(self.ambient_temperature_alert_once_timeout)
        self.ambient_temperature_alert_timer.start(20000)

    def alert_internal_temperature(self):
        print("Critical!", f"{'Internal temperature is: '}{self.data.internal_temperature}")
        QMessageBox.critical(self, "Critical", f"{'Internal temperature is: '}{self.data.internal_temperature}")
        self.internal_temperature_alert_timer = QTimer(self)
        self.internal_temperature_alert_timer.timeout.connect(self.ambient_temperature_alert_once_timeout)
        self.internal_temperature_alert_timer.start(20000)

    def alert_float_depth(self):
        print("Warning", f"{'Float depth: '}{self.data.float_depth}")
        QMessageBox.warning(self, "Warning", f"{'Float depth: '}{self.data.float_depth}")
        self.float_depth_alert_timer = QTimer(self)
        self.float_depth_alert_timer.timeout.connect(self.ambient_temperature_alert_once_timeout)
        self.float_depth_alert_timer.start(10000)

    def attitude_alert_once_timeout(self):
        self.attitude_alert_timer.stop()
        self.data.attitude_alert_once = False

    def depth_alert_once_timeout(self):
        self.depth_alert_timer.stop()
        self.data.depth_alert_once = False

    def ambient_pressure_alert_once_timeout(self):
        self.ambient_pressure_alert_timer.stop()
        self.data.ambient_pressure_alert_once = False

    def ambient_temperature_alert_once_timeout(self):
        self.ambient_temperature_alert_timer.stop()
        self.data.ambient_temperature_alert_once = False

    def internal_temperature_alert_once_timeout(self):
        self.internal_temperature_alert_timer.stop()
        self.data.internal_temperature_alert_once = False

    def float_depth_alert_once_timeout(self):
        self.float_depth_alert_timer.stop()
        self.data.float_depth_alert_once = False

