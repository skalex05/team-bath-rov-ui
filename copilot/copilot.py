import os
import time

from PyQt6.QtGui import QTextCursor, QPixmap, QImage

from vector3 import Vector3
from PyQt6.QtWidgets import QLabel, QRadioButton, QWidget, QPlainTextEdit, QGraphicsView, QPushButton, QProgressBar

from PyQt6 import QtCore

from data_interface import DataInterface
from window import Window

path_dir = os.path.dirname(os.path.realpath(__file__))

# Timer prerequisites
DURATION_INT = 900
def secs_to_minsec(secs: int):
    mins = secs // 60
    secs = secs % 60
    minsec = f'{mins:02}:{secs:02}'
    return minsec

class Copilot(Window):
    def __init__(self, *args):
        super().__init__(f"{path_dir}\\copilot.ui", *args)

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

        self.smart_repeater_temp_value: QLabel = self.findChild(QLabel, "SMARTRepeaterTempValue")
        self.mate_float_depth_value: QLabel = self.findChild(QLabel, "MATEFloatDepthValue")

        # Timer

        self.time_left_int = DURATION_INT
        self.myTimer = QtCore.QTimer(self)

        self.startTimeButton = self.findChild(QPushButton, "startTimeButton")
        self.startTimeButton.clicked.connect(self.startTimer)
        self.stopTimeButton = self.findChild(QPushButton, "stopTimeButton")
        self.stopTimeButton.clicked.connect(self.stopTimer)
        self.remainingTime = self.findChild(QLabel, "remainingTime")

        self.updateTime()

        self.progressTimeBar = self.findChild(QProgressBar, "progressTimeBar")
        self.progressTimeBar.setMinimum(0)
        self.progressTimeBar.setMaximum(DURATION_INT)


        # Actions

        self.recalibrate_imu_action: QRadioButton = self.findChild(QRadioButton, "RecalibrateIMUAction")
        self.recalibrate_imu_action.clicked.connect(self.recalibrate_imu)

        self.rov_power_action: QRadioButton = self.findChild(QRadioButton, "ROVPowerAction")
        self.rov_power_action.clicked.connect(self.on_rov_power)

        self.check_thrusters_action: QRadioButton = self.findChild(QRadioButton, "CheckThrustersAction")
        self.check_thrusters_action.clicked.connect(self.check_thrusters)

        self.check_actuators_action: QRadioButton = self.findChild(QRadioButton, "CheckActuatorsAction")
        self.check_actuators_action.clicked.connect(self.check_actuators)

        self.maintain_depth_action: QRadioButton = self.findChild(QRadioButton, "MaintainDepthAction")
        self.maintain_depth_action.clicked.connect(self.maintain_depth)

        self.main_cam: QLabel = self.findChild(QLabel, "MainCameraView")

        # Stdout

        self.stdout_window: QPlainTextEdit = self.findChild(QPlainTextEdit, "Stdout")
        self.stdout_cursor = self.stdout_window.textCursor()

    # Timer Functions

    def startTimer(self):
        if not self.myTimer.isActive():
            try:
                self.myTimer.timeout.disconnect(self.timerTimeout)
            except TypeError:
                pass

            self.myTimer.timeout.connect(self.timerTimeout)
            self.myTimer.setInterval(1000)
            self.myTimer.start()
            self.stopTimeButton.setText("Stop")

    def stopTimer(self):
        if not self.myTimer.isActive():
            self.time_left_int = DURATION_INT
            self.updateTime()
        self.myTimer.stop()
        self.stopTimeButton.setText("Reset")

    def timerTimeout(self):
        self.time_left_int -= 1

        if self.time_left_int == 0:
            self.stopTimer()

        self.updateTime()

    def updateTime(self):
        minsec = secs_to_minsec(self.time_left_int)
        self.remainingTime.setText(minsec)
        self.progressTimeBar.setValue(DURATION_INT-self.time_left_int)


    # Action Functions
    def recalibrate_imu(self, checked: bool):
        print("Recalibrating...")
        time.sleep(3)
        print("Recalibrated IMU!")
        self.recalibrate_imu_action.setChecked(False)

    def on_rov_power(self, checked: bool):
        if checked:
            print("Power On!")
        else:
            print("Power Off!")

    def check_thrusters(self, checked: bool):
        print("Checking Thrusters...")
        time.sleep(3)
        print("Thrusters working correctly")
        self.recalibrate_imu_action.setChecked(False)

    def check_actuators(self, checked: bool):
        print("Checking Arm Actuators...")
        time.sleep(3)
        print("Arm Actuators working correctly")
        self.recalibrate_imu_action.setChecked(False)

    def maintain_depth(self):
        if self.maintain_depth_action.isChecked():
            self.maintain_depth_action.setText(f"Maintaining depth ({self.app.data_interface.depth} m)")
            print(f"Maintaining depth of {self.app.data_interface.depth} m")
        else:
            print("No longer maintaining depth")

    def set_sonar_value(self, widget: QWidget, value: int, value_max: int = 200):
        if value > value_max:
            widget.setText(f">{value_max} cm")
        else:
            widget.setText(f"{value} cm")

    def update_data(self):
        # Display latest data for window
        adjust = len(self.data.lines_to_add) > 0
        for i in range(len(self.data.lines_to_add)):
            line = self.data.lines_to_add.pop()
            self.stdout_window.insertPlainText(line+"\n")

        if adjust:
            self.stdout_window.ensureCursorVisible()

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
        self.ambient_water_temp_value.setText(f"{self.data.ambient_pressure}°C")
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

        self.smart_repeater_temp_value.setText(f"{self.data.SMART_repeater_temperature} °C")
        self.mate_float_depth_value.setText(f"{self.data.SMART_repeater_temperature} m")

        if not self.maintain_depth_action.isChecked():
            self.maintain_depth_action.setText(f"Maintain Depth({self.data.depth} m)")

        frame = self.data.camera_feeds[0]
        if frame.camera_frame:
            rect = self.main_cam.geometry()
            self.main_cam.setPixmap(frame.generate_pixmap(rect.width(), rect.height()))
        else:
            self.main_cam.setText("Main Camera Is Unavailable")

        self.update()
