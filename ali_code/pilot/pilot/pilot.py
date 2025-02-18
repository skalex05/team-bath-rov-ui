import os
import sys
from PyQt6.uic import loadUi
from PyQt6.QtWidgets import QMainWindow, QFrame, QWidget, QVBoxLayout, QSizePolicy, QPushButton, QCheckBox, QLabel, QProgressBar
from PyQt6.QtCore import QThread, QTimer
from PyQt6.QtGui import QPixmap

from pilot.pilotimuRender import IMUOpenGLCube  # Import the updated OpenGL module
from datainterface.video_display import VideoDisplay
from window import Window

path_dir = os.path.dirname(os.path.realpath(__file__))

def update_pixmap(label: QLabel, pixmap: QPixmap) -> None:
    label.setPixmap(pixmap)

def display_disconnect(label: QLabel, text: str) -> None:
    label.setText(text)

class Pilot(Window):
    def __init__(self, *args):
        super().__init__(os.path.join(path_dir, "pilot.ui"), *args)
        self.solid = False

        # Setup Camera Feeds
        self.cam_displays: list[VideoDisplay] = []

        self.main_cam: QLabel = self.findChild(QLabel, "MainCameraView")
        self.secondary_1_cam: QLabel = self.findChild(QLabel, "SecondaryCameraView1")
        self.secondary_2_cam: QLabel = self.findChild(QLabel, "SecondaryCameraView2")

        self.video_handler_thread = QThread()
        for name, cam in zip(["Main Camera", "Secondary Camera 1", "Secondary Camera 2"],
                             [self.main_cam, self.secondary_1_cam, self.secondary_2_cam]):

            # Create Video Display and connect to signals
            display = VideoDisplay(cam)
            display.pixmap_ready.connect(lambda pixmap, _cam=cam: _cam.setPixmap(pixmap))
            display.on_disconnect.connect(lambda _cam=cam, _name=name: _cam.setText(f"{_name} Disconnected"))

            # Move video processing to a separate thread
            display.moveToThread(self.video_handler_thread)
            self.cam_displays.append(display)

        self.rpb_perc: QLabel = self.findChild(QLabel, "rpb_perc")
        self.rpb_kpa: QLabel = self.findChild(QLabel, "rpb_kpa")
        self.rpb_path: QFrame = self.findChild(QFrame, "RPB_PATH")

        self.temp_value: QLabel = self.findChild(QLabel, "temp_value")
        self.progressTempBar: QProgressBar = self.findChild(QProgressBar, "temp_bar")
        self.progressTempBar.setMinimum(20)
        self.progressTempBar.setMaximum(30)

        # OpenGL Integration with new structure
        placeholder_frame = self.findChild(QFrame, "openglPlaceholderFrame")
        placeholder_widget = placeholder_frame.findChild(QWidget, "openglPlaceholder") if placeholder_frame else None

        if placeholder_widget:
            self.opengl_widget = IMUOpenGLCube(port="COM3", parent=placeholder_widget)
            self.opengl_widget.setGeometry(0, 0, placeholder_widget.width(), placeholder_widget.height())
            self.opengl_widget.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
            self.opengl_widget.show()

        # Find and connect UI buttons
        self.reset_button = self.findChild(QPushButton, "resetButton")
        self.checkbox_solid = self.findChild(QCheckBox, "checkbox_solid")
        self.checkbox_mesh = self.findChild(QCheckBox, "checkbox_mesh")
        self.start_stop_button = self.findChild(QPushButton, "startstopButton")

        if self.reset_button:
            self.reset_button.clicked.connect(self.opengl_widget.reset_rotation)

        if self.checkbox_solid and self.checkbox_mesh:
            self.checkbox_solid.toggled.connect(self.handle_checkbox_toggle)
            self.checkbox_mesh.toggled.connect(self.handle_checkbox_toggle)
            self.checkbox_mesh.setChecked(True)

        if self.start_stop_button:
            self.start_stop_button.clicked.connect(self.toggle_rendering)

        self.timer = QTimer()
        self.timer.timeout.connect(self.opengl_widget.update)
        self.timer.start(16)
        self.rendering_active = True

    def handle_checkbox_toggle(self):
        if self.checkbox_solid.isChecked() and not self.solid:
            self.checkbox_mesh.setChecked(False)
            self.checkbox_solid.setChecked(True)
            self.solid = True
            self.opengl_widget.set_render_mode("solid")
        if self.checkbox_mesh.isChecked() and self.solid:
            self.checkbox_solid.setChecked(False)
            self.checkbox_mesh.setChecked(True)
            self.solid = False
            self.opengl_widget.set_render_mode("wireframe")

    def toggle_rendering(self):
        if self.rendering_active:
            self.timer.stop()
        else:
            self.timer.start(16)
        self.rendering_active = not self.rendering_active

    def attach_data_interface(self) -> None:
        self.data = self.app.data_interface
        self.data.rov_data_update.connect(self.rpb_sync)
        self.data.rov_data_update.connect(self.temp_sync)

        # Attach camera feeds to respective VideoDisplay objects
        for display, feed in zip(self.cam_displays, self.data.camera_feeds):
            display.attach_camera_feed(feed)

        self.video_handler_thread.start()

    def rpb_sync(self) -> None:
        # Gauge angle indicates the angle from 0 to 100%
        gauge_angle = 330

        value_kpa = self.data.ambient_pressure
        if not self.data.is_rov_connected():
            value_perc = 0
            value_kpa = 0
        else:
            value_perc = (value_kpa - 100) / 50

        # Update stylesheet to show the new gauge value
        val1 = (1 - value_perc * gauge_angle / 360)
        value1 = val1 - 0.001
        self.rpb_path.setStyleSheet(f"""
        #RPB_PATH{{
            background-color: qconicalgradient(cx:0.5, cy:0.5, angle: {270 - (360 - gauge_angle) / 2}, stop:{val1} rgba(85, 255, 255, 255), stop:{value1} rgba(0, 0, 124, 255));
        }}
        """)
        self.rpb_perc.setText(f"{round(value_perc * 100)}{'%'}")
        self.rpb_kpa.setText(f"{round(value_kpa)}{' kPa'}")

    def temp_sync(self) -> None:
        value_temp = self.data.ambient_temperature
        self.progressTempBar.setValue(int(value_temp))
        self.temp_value.setText(f"{round(value_temp)}{'°'}")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = Pilot(os.path.join(path_dir, "pilot.ui"))
    window.show()
    sys.exit(app.exec())
