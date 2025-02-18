import sys
from PyQt6.uic import loadUi
from PyQt6.QtWidgets import QApplication, QMainWindow, QWidget, QPushButton, QCheckBox
from PyQt6.QtCore import QTimer
from pilot.pilotimuRender import IMUOpenGLCube  # Import OpenGL rendering module

class PilotIMUInit(QMainWindow):
    def __init__(self):
        super().__init__()
        loadUi("pilot.ui", self)
        self.solid = False

        # Find OpenGL placeholder inside the new frame
        placeholder_frame = self.findChild(QFrame, "openglPlaceholderFrame")
        placeholder_widget = placeholder_frame.findChild(QWidget, "openglPlaceholder") if placeholder_frame else None

        if placeholder_widget:
            self.opengl_widget = IMUOpenGLCube(port="COM3", parent=placeholder_widget)
            self.opengl_widget.setGeometry(0, 0, placeholder_widget.width(), placeholder_widget.height())
            self.opengl_widget.show()

        # Find UI elements
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

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = PilotIMUInit()
    window.show()
    sys.exit(app.exec())
