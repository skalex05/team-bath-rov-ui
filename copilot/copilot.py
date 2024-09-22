import os

from PyQt6.QtWidgets import QLabel

from data_interface import DataInterface
from window import Window

path_dir = os.path.dirname(os.path.realpath(__file__))


class Copilot(Window):
    def __init__(self, *args):
        super().__init__(f"{path_dir}\\copilot.ui", *args)

    def set_numerical_value(self, name: str, value: int | float, value_format: str = "{}"):
        widget = self.findChild(QLabel, name)
        if widget is None:
            print(f"QLabel of name '{name}' could not be found")
            return
        widget.setText(value_format.format(value))
        widget.update()

    def set_vector_value(self, name: str, value: int | float, value_format: str = "{}"):
        widget = self.findChild(QLabel, name)
        if widget is None:
            print(f"QLabel of name '{name}'' could not be found")
            return
        value = f"{value.x:>5}, {value.y:>5}, {value.z:>5}"
        widget.setText(value_format.format(value))
        widget.update()

    def set_sonar_value(self, name: str, value: int | float, value_max=200):
        widget = self.findChild(QLabel, name)
        if widget is None:
            print(f"QLabel of name '{name}'' could not be found")
            return
        if value > value_max:
            widget.setText(f">{value_max} cm")
        else:
            widget.setText(f"{value} cm")
        widget.update()

    def update_data(self, data: DataInterface):
        # Display latest data for window

        widget = self.findChild(QLabel, "ROVAttitudeValue")
        widget.setText(f"{data.attitude.x:>6}°, {data.attitude.y:>6}°, {data.attitude.z:>6}°")
        widget.update()

        self.set_vector_value("ROVAngularAccelerationValue", data.angular_acceleration, "{} m/s")
        self.set_vector_value("ROVAngularVelocityValue", data.angular_velocity, "{} m/s")
        self.set_vector_value("ROVAccelerationValue", data.acceleration, "{} m/s")
        self.set_vector_value("ROVVelocityValue", data.velocity, "{} m/s")

        self.set_numerical_value("ROVDepthValue", data.depth, "{} m")

        self.set_numerical_value("AmbientWaterTempValue", data.ambient_temperature, "{} °C")

        self.set_numerical_value("AmbientPressureValue", data.ambient_pressure, "{} KPa")

        self.set_numerical_value("InternalTempValue", data.internal_temperature, "{} °C")

        self.set_sonar_value("MainSonarValue", data.main_sonar)
        self.set_sonar_value("FLSonarValue", data.FL_sonar)
        self.set_sonar_value("FRSonarValue", data.FR_sonar)
        self.set_sonar_value("BRSonarValue", data.BR_sonar)
        self.set_sonar_value("BLSonarValue", data.BL_sonar)

        self.set_numerical_value("Actuator1Value", data.actuator_1, "{:>3} %")
        self.set_numerical_value("Actuator2Value", data.actuator_2, "{:>3} %")
        self.set_numerical_value("Actuator3Value", data.actuator_3, "{:>3} %")
        self.set_numerical_value("Actuator4Value", data.actuator_4, "{:>3} %")
        self.set_numerical_value("Actuator5Value", data.actuator_5, "{:>3} %")
        self.set_numerical_value("Actuator6Value", data.actuator_6, "{:>3} %")

        self.set_numerical_value("SMARTRepeaterTempValue", data.SMART_repeater_temperature, "{} °C")
        self.set_numerical_value("SMARTFloatDepthValue", data.SMART_float_depth, "{} m")
