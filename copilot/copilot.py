import os

from PyQt6.QtWidgets import QLabel

from data_interface import DataInterface
from window import Window

path_dir = os.path.dirname(os.path.realpath(__file__))


class Copilot(Window):
    def __init__(self, *args):
        super().__init__(f"{path_dir}\\copilot.ui", *args)

    def update_data(self, data: DataInterface):
        # Display latest data for window
        ambient_water_temp = self.findChild(QLabel, "AmbientWaterTempValue")
        ambient_water_temp.setText(str(data.ambient_temperature))
        ambient_water_temp.update()

        ambient_pressure = self.findChild(QLabel, "AmbientPressureValue")
        ambient_pressure.setText(str(data.ambient_pressure))
        ambient_pressure.update()


