import os
import subprocess
import sys

from PyQt6.QtWidgets import QLabel, QRadioButton, QWidget, QPlainTextEdit, QPushButton, QProgressBar, QScrollArea, \
    QMessageBox

from PyQt6.QtCore import QRect, QTimer, QThread

from datainterface.data_interface import DataInterface, StdoutType
from data_classes.action_enum import ActionEnum
from datainterface.sock_stream_send import SockSend
from datainterface.video_display import VideoDisplay
from tasks.task import Task
from window import Window

path_dir = os.path.dirname(os.path.realpath(__file__))

# Timer prerequisites
DURATION_INT = 900


class Copilot(Window):
    def __init__(self, *args):
        super().__init__(os.path.join(path_dir, "copilot.ui"), *args)

        # Appearance

        self.v_pad = 5  # Amount of padding in Sensor Data Widget
        self.v_dp = 2  # Amount of decimal places displayed in numerical text in UI

        self.data: DataInterface | None = None
        self.video_handler_thread: QThread | None = None

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

        # Tasks

        self.current_title: QLabel = self.findChild(QLabel, "CurrentTitle")
        self.description: QLabel = self.findChild(QLabel, "Description")
        self.up_next_title: QLabel = self.findChild(QLabel, "UpNextTitle")
        self.complete_by_label: QLabel = self.findChild(QLabel, "CompleteBy")
        self.on_task_change()

        # Timer

        self.time_left_int = DURATION_INT

        self.startTimeButton: QPushButton = self.findChild(QPushButton, "startTimeButton")
        self.startTimeButton.clicked.connect(self.start_timer)
        self.stop_time_button: QPushButton = self.findChild(QPushButton, "stopTimeButton")
        self.stop_time_button.clicked.connect(self.stop_timer)
        self.remainingTime: QLabel = self.findChild(QLabel, "remainingTime")

        self.update_time()

        self.progressTimeBar: QProgressBar = self.findChild(QProgressBar, "progressTimeBar")
        self.progressTimeBar.setMinimum(0)
        self.progressTimeBar.setMaximum(DURATION_INT)

        self.internal_temperature_alert_timer: QTimer | None = None
        self.ambient_temperature_alert_timer: QTimer | None = None
        self.ambient_pressure_alert_timer: QTimer | None = None
        self.depth_alert_timer: QTimer | None = None
        self.float_depth_alert_timer: QTimer | None = None
        self.attitude_alert_timer: QTimer | None = None

        # Actions

        self.connection_debounce = False

        self.recalibrate_imu_action: QRadioButton = self.findChild(QRadioButton, "RecalibrateIMUAction")
        self.recalibrate_imu_action.clicked.connect(self.recalibrate_imu)

        self.rov_power_action: QRadioButton = self.findChild(QRadioButton, "ROVPowerAction")
        self.rov_power_action.clicked.connect(self.on_rov_power)
        self.con_timer = None

        self.maintain_depth_action: QRadioButton = self.findChild(QRadioButton, "MaintainDepthAction")
        self.maintain_depth_action.clicked.connect(self.maintain_depth)

        self.reinitialise_cameras_action: QRadioButton = self.findChild(QRadioButton, "ReinitialiseCameras")
        self.reinitialise_cameras_action.clicked.connect(self.reinitialise_cameras)

        self.connect_float_action: QRadioButton = self.findChild(QRadioButton, "ConnectFloatAction")
        self.connect_float_action.clicked.connect(self.connect_float)

        self.disable_alerts_action: QRadioButton = self.findChild(QRadioButton, "DisableAlerts")
        self.disable_alerts_action.clicked.connect(self.disable_alerts)

        self.main_cam: QLabel = self.findChild(QLabel, "MainCameraView")
        self.main_cam_display = VideoDisplay(self.main_cam, self.app, True)
        self.main_cam_display.pixmap_ready.connect(lambda pixmap: self.main_cam.setPixmap(pixmap))
        self.main_cam_display.on_disconnect.connect(lambda: self.main_cam.setText("Main Camera Disconnected"))

        self.video_handler_thread = QThread()
        self.main_cam_display.moveToThread(self.video_handler_thread)

        # Stdout

        self.stdout_window: QPlainTextEdit = self.findChild(QPlainTextEdit, "Stdout")
        self.stdout_cursor = self.stdout_window.textCursor()

        # Tasks

        self.task_list: QScrollArea = self.findChild(QScrollArea, "TaskList")
        self.task_list_contents: QWidget = self.task_list.findChild(QWidget, "TaskListContents")
        self.build_task_widgets()

        self.all_alerts_disabled = False

        self.app.task_checked.connect(self.on_task_change)

    def on_task_change(self) -> None:
        # Find out which tasks need to be displayed.
        # Current and next tasks are not necessarily contiguous
        # Also no guarantee there is a current/next task
        current: Task | None = None
        up_next: Task | None = None

        for task in self.app.tasks:
            if not task.completed:
                if current is None:
                    current = task
                else:
                    up_next = task
                    break
        if current:
            self.current_title.setText(current.title)
            self.description.setText(current.description)
        else:
            # If there's no current task, all tasks are complete
            self.current_title.setText("All Tasks Complete")
            self.description.setText("Congratulations!")
            self.up_next_title.setText("")
            self.complete_by_label.setText("")
        # Display next task if applicable
        if up_next:
            self.up_next_title.setText(up_next.title)
            self.complete_by_label.setText(f"Complete By: {up_next.start_time[0]:02} : {up_next.start_time[1]:02}")
        else:
            self.up_next_title.setText("")
            self.complete_by_label.setText(f"Complete By: {DURATION_INT // 60}:{DURATION_INT % 60}")

    def attach_data_interface(self) -> None:
        self.data = self.app.data_interface

        self.data.rov_data_update.connect(self.update_rov_data)
        self.data.rov_data_thread.on_disconnect.connect(self.on_rov_disconnect)
        self.data.rov_data_thread.on_connect.connect(self.on_rov_connect)

        self.data.float_data_update.connect(self.update_float_data)
        self.data.float_data_thread.on_disconnect.connect(self.on_float_disconnect)
        self.data.float_data_thread.on_connect.connect(self.on_float_connect)

        self.data.stdout_update.connect(self.update_stdout)

        # Alert connect
        self.data.attitude_alert.connect(self.alert_attitude)
        self.data.depth_alert.connect(self.alert_depth)
        self.data.ambient_pressure_alert.connect(self.alert_ambient_pressure)
        self.data.ambient_temperature_alert.connect(self.alert_ambient_temperature)
        self.data.internal_temperature_alert.connect(self.alert_internal_temperature)
        self.data.float_depth_alert.connect(self.alert_float_depth)

        self.main_cam_display.attach_camera_feed(self.data.camera_feeds[0])

        self.video_handler_thread.start()

    # Timer Functions

    @staticmethod
    def secs_to_minsec(secs: int) -> str:
        # Format seconds to minutes and seconds
        mins = secs // 60
        secs = secs % 60
        minsec = f'{mins:02}:{secs:02}'
        return minsec

    def start_timer(self) -> None:
        if not self.data.timer.isActive():
            try:
                self.data.timer.timeout.disconnect(self.timer_timeout)
            except TypeError:
                pass

            self.data.timer.timeout.connect(self.timer_timeout)
            self.data.timer.setInterval(1000)
            self.data.timer.start()
            self.stop_time_button.setText("Stop")

    def stop_timer(self) -> None:
        if not self.data.timer.isActive():
            # If the timer is inactive, reset the timer
            self.time_left_int = DURATION_INT
            self.app.reset_task_completion()
            self.update_time()
        self.data.timer.stop()
        self.stop_time_button.setText("Reset")

    def timer_timeout(self) -> None:
        self.time_left_int -= 1

        if self.time_left_int == 0:
            self.stop_timer()

        self.update_time()

    def update_time(self) -> None:
        minsec = Copilot.secs_to_minsec(self.time_left_int)
        self.remainingTime.setText(minsec)
        self.progressTimeBar.setValue(DURATION_INT - self.time_left_int)

    def build_task_widgets(self) -> None:
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
    def recalibrate_imu(self) -> None:
        print("RECALIBRATION NOT IMPLEMENTED")
        self.recalibrate_imu_action.setChecked(False)

    def on_rov_power(self) -> None:
        def on_timeout(msg, con=True):
            if self.data.is_rov_connected() == con:
                return
            print(msg, file=sys.stderr)
            self.connection_debounce = False
            self.con_timer.stop()

        if self.connection_debounce:
            return
        if not self.data.is_rov_connected():
            self.rov_power_action.setChecked(False)
            self.connection_debounce = True
            self.con_timer = QTimer()
            self.con_timer.timeout.connect(lambda: on_timeout("Couldn't connect to ROV"))
            self.con_timer.start(5000)
            if self.app.local_test:
                if os.name == "nt":
                    ex = "python.exe"
                else:
                    ex = "python3"
                subprocess.Popen([ex, "rov_interface.py"])
            else:
                SockSend(self.app, self.app.ROV_IP, 52528, ActionEnum.POWER_ON_ROV)
        else:
            self.rov_power_action.setChecked(True)
            response = QMessageBox.warning(None, f"Power Off Warning", f"Are you sure you want to turn off the ROV?",
                                           QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                                           QMessageBox.StandardButton.No
                                           )
            if response == QMessageBox.StandardButton.No:
                return
            self.connection_debounce = True
            self.con_timer = QTimer()
            self.con_timer.timeout.connect(lambda: on_timeout("Couldn't power off the ROV", con=False))
            self.con_timer.start(5000)
            print("Power Off!")
            SockSend(self.app, self.app.ROV_IP, 52527, ActionEnum.POWER_OFF_ROV)

    def maintain_depth(self) -> None:
        if self.data.is_rov_connected():
            depth = self.data.depth
            checked = self.maintain_depth_action.isChecked()
            SockSend(self.app, self.app.ROV_IP, 52527, (ActionEnum.MAINTAIN_ROV_DEPTH, checked, depth))

            if checked:
                self.maintain_depth_action.setText(f"Maintaining Depth ({depth:.{self.v_dp}f} m)")
                return
        self.maintain_depth_action.setChecked(False)
        self.maintain_depth_action.setText("Maintain Depth")

    def reinitialise_cameras(self) -> None:
        # Check cameras aren't already being initialised
        if self.data.is_rov_connected():
            SockSend(self.app, self.app.ROV_IP, 52527, ActionEnum.REINIT_CAMS)
        self.reinitialise_cameras_action.setChecked(False)

    def disable_alerts(self) -> None:
        if not self.all_alerts_disabled:
            self.data.attitude_alert_once = True
            self.data.depth_alert_once = True
            self.data.ambient_temperature_alert_once = True
            self.data.ambient_pressure_alert_once = True
            self.data.internal_temperature_alert_once = True
            self.data.float_depth_alert_once = True
            self.all_alerts_disabled = True
            print("Alerts disabled")
        else:
            self.data.attitude_alert_once = False
            self.data.depth_alert_once = False
            self.data.ambient_temperature_alert_once = False
            self.data.ambient_pressure_alert_once = False
            self.data.internal_temperature_alert_once = False
            self.data.float_depth_alert_once = False
            self.all_alerts_disabled = False
            self.all_alerts_disabled = False
            print("Alerts re-enabled")

    def connect_float(self) -> None:
        if self.app.float_data_source_proc is None:
            self.connect_float_action.setChecked(False)
            self.app.float_data_source_proc = True
            try:
                self.app.float_data_source_proc = subprocess.Popen(
                    ["python.exe", "datainterface//float_data_source.py"])
            except FileNotFoundError:
                self.app.float_data_source_proc = subprocess.Popen(["python3", "datainterface//float_data_source.py"])
            print("Connected!")
            self.connect_float_action.setText("Disconnect Float")
        else:
            self.connect_float_action.setChecked(True)
            self.app.float_data_source_proc.terminate()
            self.app.float_data_source_proc = None
            print("Disconnected!")
            self.connect_float_action.setText("Connect Float")

    def update_stdout(self, source, line) -> None:
        sources = {
            StdoutType.UI: "UI",
            StdoutType.UI_ERROR: "UI ERR",
            StdoutType.ROV: "ROV",
            StdoutType.ROV_ERROR: "ROV ERR"
        }

        source_str = sources[source]

        # Display latest data for window
        str_header = f"[{source_str}] - "
        line = str_header + line.replace("\n", "\n"+" " * len(str_header))

        self.stdout_window.appendPlainText(line)

        # Scroll to bottom if scrollbar is less than 5 from bottom
        if self.stdout_window.verticalScrollBar().maximum() - self.stdout_window.verticalScrollBar().value() < 5:
            self.stdout_window.ensureCursorVisible()

    def update_rov_data(self) -> None:
        t = self.data.attitude
        self.rov_attitude_value.setText(
            f"{t.x:<{self.v_pad}.{self.v_dp}f}°, {t.y:<{self.v_pad}.{self.v_dp}f}°, {t.z:<{self.v_pad}.{self.v_dp}f}°")

        # Update all acceleration/velocity readings
        for val, label in zip([self.data.angular_acceleration, self.data.angular_velocity,
                               self.data.acceleration, self.data.velocity],
                              [self.rov_angular_accel_value, self.rov_angular_velocity_value,
                               self.rov_acceleration_value, self.rov_velocity_value]):
            label.setText(f"{val.x:<{self.v_pad}.{self.v_dp}f}, "
                          f"{val.y:<{self.v_pad}.{self.v_dp}f}, "
                          f"{val.z:<{self.v_pad}.{self.v_dp}f} m/s")

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

        if not self.maintain_depth_action.isChecked():
            self.maintain_depth_action.setText("Maintain Depth")

    def on_rov_connect(self) -> None:
        self.rov_power_action.setChecked(True)
        self.connection_debounce = False

    def on_rov_disconnect(self) -> None:
        self.rov_power_action.setChecked(False)
        self.connection_debounce = False
        for label in [self.rov_attitude_value, self.rov_angular_accel_value, self.rov_angular_velocity_value,
                      self.rov_acceleration_value, self.rov_velocity_value, self.rov_depth_value,
                      self.ambient_pressure_value, self.ambient_water_temp_value, self.internal_temp_value,
                      self.actuator1_value, self.actuator2_value, self.actuator3_value,
                      self.actuator4_value, self.actuator5_value, self.actuator6_value]:
            label.setText("ROV Disconnected")
        if self.maintain_depth_action.isChecked():
            self.maintain_depth_action.setChecked(False)

    def update_float_data(self) -> None:
        self.float_depth_value.setText(f"{self.data.float_depth} m")

    def on_float_connect(self) -> None:
        self.connect_float_action.setChecked(True)

    def on_float_disconnect(self) -> None:
        self.connect_float_action.setChecked(False)
        self.float_depth_value.setText("Float Disconnected")

    # Alert messages, need upgrade
    def alert_attitude(self) -> None:
        print("Warning!", f"{'Roll is: '}{self.data.attitude.z}")
        QMessageBox.warning(self, "Warning", f"{'Roll is: '}{self.data.attitude.z}")
        self.attitude_alert_timer = QTimer(self)
        self.attitude_alert_timer.timeout.connect(self.attitude_alert_once_timeout)
        self.attitude_alert_timer.start(20000)

    def alert_depth(self) -> None:
        print("Warning!", f"{'Depth is: '}{self.data.depth}")
        QMessageBox.warning(self, "Warning", f"{'Depth is: '}{self.data.depth}")
        self.depth_alert_timer = QTimer(self)
        self.depth_alert_timer.timeout.connect(self.depth_alert_once_timeout)
        self.depth_alert_timer.start(20000)

    def alert_ambient_pressure(self) -> None:
        print("Warning!", f"{'Ambient pressure is: '}{self.data.ambient_pressure}")
        QMessageBox.warning(self, "Warning", f"{'Ambient pressure is: '}{self.data.ambient_pressure}")
        self.ambient_pressure_alert_timer = QTimer(self)
        self.ambient_pressure_alert_timer.timeout.connect(self.ambient_pressure_alert_once_timeout)
        self.ambient_pressure_alert_timer.start(20000)

    def alert_ambient_temperature(self) -> None:
        print("Warning!", f"{'Ambient temperature is: '}{self.data.ambient_temperature}")
        QMessageBox.warning(self, "Warning", f"{'Ambient temperature is: '}{self.data.ambient_temperature}")
        self.ambient_temperature_alert_timer = QTimer(self)
        self.ambient_temperature_alert_timer.timeout.connect(self.ambient_temperature_alert_once_timeout)
        self.ambient_temperature_alert_timer.start(20000)

    def alert_internal_temperature(self) -> None:
        print("Critical!", f"{'Internal temperature is: '}{self.data.internal_temperature}")
        QMessageBox.critical(self, "Critical", f"{'Internal temperature is: '}{self.data.internal_temperature}")
        self.internal_temperature_alert_timer = QTimer(self)
        self.internal_temperature_alert_timer.timeout.connect(self.internal_temperature_alert_once_timeout)
        self.internal_temperature_alert_timer.start(20000)

    def alert_float_depth(self) -> None:
        print("Warning", f"{'Float depth: '}{self.data.float_depth}")
        QMessageBox.warning(self, "Warning", f"{'Float depth: '}{self.data.float_depth}")
        self.float_depth_alert_timer = QTimer(self)
        self.float_depth_alert_timer.timeout.connect(self.float_depth_alert_once_timeout)
        self.float_depth_alert_timer.start(10000)

    def attitude_alert_once_timeout(self) -> None:
        self.attitude_alert_timer.stop()
        if not self.all_alerts_disabled:
            self.data.attitude_alert_once = False

    def depth_alert_once_timeout(self) -> None:
        self.depth_alert_timer.stop()
        if not self.all_alerts_disabled:
            self.data.depth_alert_once = False

    def ambient_pressure_alert_once_timeout(self) -> None:
        self.ambient_pressure_alert_timer.stop()
        if not self.all_alerts_disabled:
            self.data.ambient_pressure_alert_once = False

    def ambient_temperature_alert_once_timeout(self) -> None:
        self.ambient_temperature_alert_timer.stop()
        if not self.all_alerts_disabled:
            self.data.ambient_temperature_alert_once = False

    def internal_temperature_alert_once_timeout(self) -> None:
        self.internal_temperature_alert_timer.stop()
        if not self.all_alerts_disabled:
            self.data.internal_temperature_alert_once = False

    def float_depth_alert_once_timeout(self) -> None:
        self.float_depth_alert_timer.stop()
        if not self.all_alerts_disabled:
            self.data.float_depth_alert_once = False
