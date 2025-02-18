from PyQt6.QtOpenGLWidgets import QOpenGLWidget
from OpenGL.GL import *
from OpenGL.GLU import *
import serial
import time
import re

class IMUOpenGLCube(QOpenGLWidget):
    def __init__(self, port, parent=None):
        super().__init__(parent)
        self.port = port
        self.serial_connection = serial.Serial(self.port, 115200, timeout=0.1)
        time.sleep(2)

        self.vertices = [
            (1, 1, -1), (1, -1, -1), (-1, -1, -1), (-1, 1, -1),
            (1, 1, 1), (1, -1, 1), (-1, -1, 1), (-1, 1, 1)
        ]

        self.faces = [
            (0, 1, 2, 3),  # Front
            (3, 2, 6, 7),  # Right
            (7, 6, 5, 4),  # Back
            (4, 5, 1, 0),  # Left
            (1, 5, 6, 2),  # Top
            (4, 0, 3, 7)   # Bottom
        ]

        self.colors = [
            (1, 0, 1),  # Magenta - Front
            (1, 1, 0),  # Yellow - Right
            (1, 0, 0),  # Red - Back
            (0, 0, 1),  # Blue - Left
            (0, 1, 1),  # Cyan - Top
            (0, 1, 0)   # Green - Bottom
        ]

        self.rotation_x, self.rotation_y, self.rotation_z = 0, 0, 0
        self.gyro_x, self.gyro_y, self.gyro_z, self.temperature = 0.0, 0.0, 0.0, 0.0
        self.last_time = time.time()
        self.render_mode = "wireframe"

    def set_render_mode(self, mode):
        if mode in ["solid", "wireframe"]:
            self.render_mode = mode
        self.update()

    def initializeGL(self):
        glClearColor(0.0, 0.0, 0.0, 1.0)
        glEnable(GL_DEPTH_TEST)

    def resizeGL(self, width, height):
        glViewport(0, 0, width, height)
        glMatrixMode(GL_PROJECTION)
        glLoadIdentity()
        gluPerspective(45, (width / height), 0.1, 50.0)
        glTranslatef(0.0, 0.0, -5)
        glMatrixMode(GL_MODELVIEW)

    def paintGL(self):
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        glLoadIdentity()
        self.update_rotation()

        glPushMatrix()
        glRotatef(self.rotation_x * (180 / 3.14159), 0, 0, 1)
        glRotatef(self.rotation_y * (180 / 3.14159), 1, 0, 0)
        glRotatef(self.rotation_z * (180 / 3.14159), 0, 1, 0)

        self.draw_cube()
        glPopMatrix()

    def draw_cube(self):
        if self.render_mode == "solid":
            self.draw_solid_cube()
        else:
            self.draw_wireframe_cube()

    def draw_wireframe_cube(self):
        glBegin(GL_LINES)
        for edge in [(0, 1), (1, 2), (2, 3), (3, 0), (4, 5), (5, 6), (6, 7), (7, 4), (0, 4), (1, 5), (2, 6), (3, 7)]:
            glColor3f(1, 1, 1)
            for vertex in edge:
                glVertex3fv(self.vertices[vertex])
        glEnd()

    def draw_solid_cube(self):
        glBegin(GL_QUADS)
        for i, face in enumerate(self.faces):
            glColor3fv(self.colors[i])
            for vertex in face:
                glVertex3fv(self.vertices[vertex])
        glEnd()

    def update_rotation(self):
        if self.serial_connection.in_waiting > 0:
            data = self.serial_connection.readline().decode("utf-8").strip()
            match = re.match(r"X: ([\d.-]+) Y: ([\d.-]+) Z: ([\d.-]+)", data)
            if match:
                self.gyro_x, self.gyro_y, self.gyro_z = map(float, match.groups())
                dt = time.time() - self.last_time
                self.last_time = time.time()
                self.rotation_x += self.gyro_x * dt
                self.rotation_y += self.gyro_y * dt
                self.rotation_z += self.gyro_z * dt

    def reset_rotation(self):
        self.rotation_x = self.rotation_y = self.rotation_z = 0
        self.update()
