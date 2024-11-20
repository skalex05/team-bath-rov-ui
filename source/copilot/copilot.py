import os
import subprocess
import time

from PyQt6.QtWidgets import QLabel, QRadioButton, QWidget, QPlainTextEdit, QPushButton, QProgressBar, QScrollArea, QMessageBox

from PyQt6.QtCore import QRect

from data_interface.data_interface import DataInterface
from action_thread import ActionThread
from window import Window

path_dir = os.path.dirname(os.path.realpath(__file__))

# Timer prerequisites
DURATION_INT = 900


class Copilot(Window):
    def __init__(self, *args):
        super().__init__(os.path.join(path_dir, "copilot.ui"), *args)

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

        self.main_sonar_value: QLabel = self.findChild(QLabel, "MainSonarValue")
        self.FL_sonar_value: QLabel = self.findChild(QLabel, "FLSonarValue")
        self.FR_sonar_value: QLabel = self.findChild(QLabel, "FRSonarValue")
        self.BR_sonar_value: QLabel = self.findChild(QLabel, "BRSonarValue")
        self.BL_sonar_value: QLabel = self.findChild(QLabel, "BLSonarValue")

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

        self.check_thrusters_action: QRadioButton = self.findChild(QRadioButton, "CheckThrustersAction")
        self.check_thrusters_action_thread = ActionThread(self.check_thrusters_action,
                                                          target=self.check_thrusters)

        self.check_actuators_action: QRadioButton = self.findChild(QRadioButton, "CheckActuatorsAction")
        self.check_actuators_action_thread = ActionThread(self.check_actuators_action,
                                                          target=self.check_actuators)

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
            self.rov_power_action.setChecked(False)
            self.app.rov_data_source_proc = subprocess.Popen(["python.exe", "data_interface//rov_data_source.py"])
            print("Powering On!")
            time.sleep(2)
            print("Power On!")
            self.rov_power_action.setChecked(True)
        else:
            self.rov_power_action.setChecked(True)
            print("Powering Off!")
            self.app.rov_data_source_proc.terminate()
            self.app.rov_data_source_proc = None
            time.sleep(2)
            print("Power Off!")
            self.rov_power_action.setChecked(False)

    def check_thrusters(self):
        print("Checking Thrusters...")
        time.sleep(3)
        print("Thrusters working correctly")

    def check_actuators(self):
        print("Checking Arm Actuators...")
        time.sleep(3)
        print("Arm Actuators working correctly")

    def maintain_depth(self):
        if self.maintain_depth_action.isChecked():
            self.maintain_depth_action.setText(f"Maintaining depth ({self.app.data_interface.depth} m)")
            print(f"Maintaining depth of {self.app.data_interface.depth} m")
        else:
            print("No longer maintaining depth")

    def reinitialise_cameras(self):
        # Check cameras aren't already being initialised
        finished = True
        for camera in self.data.camera_feeds:
            finished = finished and not camera.initialising

        if finished:
            # User must wait for all cameras to finish reinitialising before starting again
            for feed in self.data.camera_feeds:
                if feed.initialising:
                    return

            for feed in self.data.camera_feeds:
                feed.start_init_camera_feed()

        finished = False
        initialised = True
        while not finished:
            initialised = True
            finished = True
            for camera in self.data.camera_feeds:
                finished = finished and not camera.initialising
                initialised = initialised and camera.initialised

        if initialised:
            print("All Cameras Initialised Successfully!")
        else:
            print("Some cameras failed to initialise. Try again.")

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

    @staticmethod
    def set_sonar_value(widget: QWidget, value: int, value_max: int = 200):
        if value > value_max:
            widget.setText(f">{value_max} cm")
        else:
            widget.setText(f"{value} cm")

    def connect_float(self):
        if self.connect_float_action.isChecked():
            self.connect_float_action.setChecked(False)
            self.app.float_data_source_proc = subprocess.Popen(["python.exe", "data_interface//float_data_source.py"])
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

    def update_stdout(self):
        # Display latest data for window
        adjust = len(self.data.lines_to_add) > 0
        for i in range(len(self.data.lines_to_add)):
            line = self.data.lines_to_add.popleft()
            self.stdout_window.insertPlainText(line + "\n")

        if adjust:
            self.stdout_window.ensureCursorVisible()

    def update_rov_data(self):
        if self.data.rov_connected:
            t = self.data.attitude
            self.rov_attitude_value.setText(f"{t.x:<5}°, {t.y:<5}°, {t.z:<5}°")
            t = self.data.angular_acceleration
            self.rov_angular_accel_value.setText(f"{t.x:<5}, {t.y:<5}, {t.z:<5} m/s")
            t = self.data.angular_velocity
            self.rov_angular_velocity_value.setText(f"{t.x:<5}, {t.y:<5}, {t.z:<5} m/s")
            t = self.data.acceleration
            self.rov_acceleration_value.setText(f"{t.x:<5}, {t.y:<5}, {t.z:<5} m/s")
            t = self.data.velocity
            self.rov_velocity_value.setText(f"{t.x:<5}, {t.y:<5}, {t.z:<5} m/s")

            self.rov_depth_value.setText(f"{self.data.depth} m")
            self.ambient_water_temp_value.setText(f"{self.data.ambient_temperature}°C")
            self.ambient_pressure_value.setText(f"{self.data.ambient_pressure} KPa")
            self.internal_temp_value.setText(f"{self.data.internal_temperature} °C")

            self.set_sonar_value(self.main_sonar_value, self.data.main_sonar)
            self.set_sonar_value(self.FR_sonar_value, self.data.FR_sonar)
            self.set_sonar_value(self.FL_sonar_value, self.data.FL_sonar)
            self.set_sonar_value(self.BR_sonar_value, self.data.BR_sonar)
            self.set_sonar_value(self.BL_sonar_value, self.data.BL_sonar)

            self.actuator1_value.setText(f"{self.data.actuator_1:>3} %")
            self.actuator2_value.setText(f"{self.data.actuator_2:>3} %")
            self.actuator3_value.setText(f"{self.data.actuator_3:>3} %")
            self.actuator4_value.setText(f"{self.data.actuator_4:>3} %")
            self.actuator5_value.setText(f"{self.data.actuator_5:>3} %")
            self.actuator6_value.setText(f"{self.data.actuator_6:>3} %")

        else:
            pass

            for label in [self.rov_attitude_value, self.rov_angular_accel_value, self.rov_angular_velocity_value,
                          self.rov_acceleration_value, self.rov_velocity_value, self.rov_depth_value,
                          self.ambient_pressure_value, self.ambient_water_temp_value, self.internal_temp_value,
                          self.main_sonar_value, self.FR_sonar_value, self.FL_sonar_value, self.BR_sonar_value,
                          self.BL_sonar_value, self.actuator1_value, self.actuator2_value, self.actuator3_value,
                          self.actuator4_value, self.actuator5_value, self.actuator6_value]:
                label.setText("ROV Disconnected")

        if not self.maintain_depth_action.isChecked():
            self.maintain_depth_action.setText(f"Maintain Depth({self.data.depth} m)")

    def update_float_data(self):
        if self.data.float_connected:
            self.float_depth_value.setText(f"{self.data.float_depth} m")
        else:
            self.float_depth_value.setText("Float Disconnected")

    def update_video(self, i: int):
        if i != 0:
            return
        try:
            frame = self.data.camera_feeds[0]
            if frame.camera_frame:
                rect = self.main_cam.geometry()
                self.main_cam.setPixmap(frame.generate_pixmap(rect.width(), rect.height()))
            else:
                raise IndexError()
        except IndexError:
            self.main_cam.setText("Main Camera Is Unavailable")

        self.update()

    # Alert messages, need upgrade
    def alert_attitude(self):
        QMessageBox.warning(self, "Warning", f"{'Roll is: '}{self.data.attitude.z}")

    def alert_depth(self):
        QMessageBox.warning(self, "Depth warning", f"{'Depth is: '}{self.data.depth}")

    def alert_ambient_pressure(self):
        QMessageBox.warning(self, "Warning", f"{'Ambient pressure is: '}{self.data.ambient_pressure}")

    def alert_ambient_temperature(self):
        QMessageBox.warning(self, "Warning", f"{'Ambient temperature is: '}{self.data.ambient_temperature}")

    def alert_internal_temperature(self):
        QMessageBox.critical(self, "Critical", f"{'Internal temperature is: '}{self.data.internal_temperature}")

    def alert_float_depth(self):
        QMessageBox.warning(self, "Warning", f"{'Float depth: '}{self.data.float_depth}")
