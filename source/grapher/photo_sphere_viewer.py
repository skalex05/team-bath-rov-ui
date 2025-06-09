import ctypes
import sys

import numpy as np
import pillow_heif

from OpenGL.GL import *
from OpenGL.GL.shaders import compileProgram, compileShader
from OpenGL.GLU import gluNewQuadric
from OpenGL.raw.GLU import gluQuadricTexture, gluQuadricOrientation, GLU_INSIDE, gluPerspective, gluSphere, GLU_OUTSIDE
from PIL import ImageOps, Image

from PyQt6.QtGui import QSurfaceFormat
from PyQt6.QtCore import QSize, Qt, QTimer
from PyQt6.QtOpenGLWidgets import QOpenGLWidget
from PyQt6.QtWidgets import QApplication
from PyQt6.QtOpenGL import QOpenGLVersionProfile


class PhotosphereViewer(QOpenGLWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.fmt = None
        self.initialised = False
        self.image_path = None
        self.rot_x = 0.0
        self.rot_y = 0.0
        self.rot_z = 0.0
        self.rot_speed = 1.0
        self.width = None
        self.height = None
        self.texture = None
        self.quadric = None

        # Set focus policy to receive key events
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

        # Use compatibility profile for legacy OpenGL calls
        fmt = self.format()
        fmt.setVersion(2, 1)
        fmt.setProfile(QSurfaceFormat.OpenGLContextProfile.CompatibilityProfile)
        self.setFormat(fmt)

        # Timer for animation
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update)
        self.timer.start(16)  # ~60fps (16ms per frame)

    def set_image_path(self, image_path: str):
        self.image_path = image_path
        # Only load texture if we're already initialized and have a valid context
        if self.initialised and self.isValid():
            self.makeCurrent()
            self.load_texture()
            self.update()
        elif self.image_path:
            # If not initialized yet, texture will be loaded in initializeGL
            print("Image path set, texture will be loaded when OpenGL context is ready")
        self.reset_rotation()

    def initializeGL(self) -> None:
        self.initialised = False
        try:
            print(f"Running OpenGL {glGetString(GL_VERSION).decode('utf-8')}")
            print(f"GPU Vendor: {glGetString(GL_VENDOR).decode('utf-8')}")
            print(f"Renderer: {glGetString(GL_RENDERER).decode('utf-8')}")

            context = self.context()
            format = context.format()

            print("OpenGL Context Properties:")
            print(f"OpenGL Version: {format.majorVersion()}.{format.minorVersion()}")
            print(
                f"Profile: {'Core' if format.profile() == QSurfaceFormat.OpenGLContextProfile.CoreProfile else 'Compatibility'}")
            print(f"Hardware Accelerated: {not context.isOpenGLES()}")

            # Enable debug output if available
            try:
                glEnable(GL_DEBUG_OUTPUT)
                glEnable(GL_DEBUG_OUTPUT_SYNCHRONOUS)

                def debug_callback(source, msg_type, msg_id, severity, length, message, user_param):
                    print(f"OpenGL Debug: {message.decode('utf-8')}")

                debug_callback_ptr = GLDEBUGPROC(debug_callback)
                glDebugMessageCallback(debug_callback_ptr, None)
                glDebugMessageControl(GL_DONT_CARE, GL_DONT_CARE, GL_DONT_CARE, 0, None, GL_TRUE)
            except:
                print("Debug output not available")

            if not self.isValid():
                print("OpenGL Context is not valid", file=sys.stderr)
                return

            if self.image_path is None:
                print("No photosphere image to display")
                return

            # OpenGL settings
            glEnable(GL_TEXTURE_2D)
            glClearColor(0.0, 0.0, 0.0, 1.0)
            glEnable(GL_DEPTH_TEST)

            # Load texture if image path is set
            if self.image_path:
                self.load_texture()

            # Create quadric for sphere
            self.quadric = gluNewQuadric()
            gluQuadricTexture(self.quadric, GL_TRUE)
            gluQuadricOrientation(self.quadric, GLU_INSIDE)  # Inside for photosphere

            self.initialised = True
            print("OpenGL initialized successfully")

        except Exception as e:
            print(f"OpenGL initialization error: {e}", file=sys.stderr)
            import traceback
            traceback.print_exc()

    def resizeGL(self, width, height):
        """Handle window resize - setup projection matrix here"""
        if height == 0:
            height = 1

        glViewport(0, 0, width, height)

        # Set projection matrix
        glMatrixMode(GL_PROJECTION)
        glLoadIdentity()
        gluPerspective(45.0, width / height, 0.1, 100.0)

        # Switch back to modelview matrix
        glMatrixMode(GL_MODELVIEW)

    def load_texture(self):
        """Load and bind texture from image file"""
        # Ensure we have a valid OpenGL context
        if not self.isValid():
            print("OpenGL context is not valid, cannot load texture")
            return

        # Make sure this context is current
        self.makeCurrent()

        try:
            pillow_heif.register_heif_opener()
            img = Image.open(self.image_path)

            # Flip image vertically for OpenGL texture coordinates
            img = ImageOps.flip(img)
            img_data = img.convert("RGB").tobytes()
            self.width, self.height = img.size

            # Generate and bind texture
            if self.texture:
                glDeleteTextures([self.texture])

            self.texture = glGenTextures(1)
            glBindTexture(GL_TEXTURE_2D, self.texture)

            # Set texture parameters
            glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_REPEAT)
            glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_REPEAT)
            glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
            glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)

            # Upload texture data
            glPixelStorei(GL_UNPACK_ALIGNMENT, 1)
            glTexImage2D(GL_TEXTURE_2D, 0, GL_RGB, self.width, self.height, 0, GL_RGB, GL_UNSIGNED_BYTE, img_data)

            print(f"Texture loaded successfully: {self.width}x{self.height}, ID: {self.texture}")

        except Exception as e:
            print(f"Error loading texture: {e}", file=sys.stderr)
            import traceback
            traceback.print_exc()

    # Don't call doneCurrent() here as it might be needed by the caller

    def paintGL(self):
        """Render the photosphere"""
        if not self.initialised or not self.isValid():
            return

        try:
            # Ensure context is current
            if not self.context().isValid():
                print("OpenGL context became invalid")
                return

            # Clear buffers
            glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
            glLoadIdentity()

            # Bind texture
            if self.texture:
                glBindTexture(GL_TEXTURE_2D, self.texture)

            # Apply rotations for camera movement
            glRotatef(self.rot_x, 1, 0, 0)
            glRotatef(self.rot_y, 0, 1, 0)
            glRotatef(self.rot_z, 0, 0, 1)

            # Draw textured sphere (larger radius for photosphere effect)
            if self.quadric:
                gluSphere(self.quadric, 10.0, 60, 60)

        except Exception as e:
            print(f"OpenGL paint error: {e}", file=sys.stderr)

    def keyPressEvent(self, event):
        """Handle keyboard input for camera rotation"""
        key = event.key()

        if key == Qt.Key.Key_S:
            self.rot_x += self.rot_speed
        elif key == Qt.Key.Key_W:
            self.rot_x -= self.rot_speed
        elif key == Qt.Key.Key_E:
            self.rot_y -= self.rot_speed
        elif key == Qt.Key.Key_Q:
            self.rot_y += self.rot_speed
        elif key == Qt.Key.Key_D:
            self.rot_z += self.rot_speed
        elif key == Qt.Key.Key_A:
            self.rot_z -= self.rot_speed
        elif key == Qt.Key.Key_R:
            # Reset rotation
            self.rot_x = self.rot_y = self.rot_z = 0.0
        elif key == Qt.Key.Key_Escape:
            # Exit application
            QApplication.quit()

        # Keep rotations within reasonable bounds
        self.rot_x = self.rot_x % 360.0
        self.rot_y = self.rot_y % 360.0
        self.rot_z = self.rot_z % 360.0

        self.update()

    def mousePressEvent(self, event):
        """Store mouse position for drag operations"""
        self.last_mouse_pos = event.pos()

    def mouseMoveEvent(self, event):
        """Handle mouse drag for camera rotation"""
        if hasattr(self, 'last_mouse_pos'):
            dx = event.pos().x() - self.last_mouse_pos.x()
            dy = event.pos().y() - self.last_mouse_pos.y()

            # Convert mouse movement to rotation
            self.rot_z -= dx * 0.1
            self.rot_x -= dy * 0.1

            # Keep rotations within bounds
            self.rot_x = self.rot_x % 360.0
            self.rot_z = self.rot_z % 360.0

            self.last_mouse_pos = event.pos()
            self.update()

    def reset_rotation(self):
        self.rot_x = 0
        self.rot_y = 0
        self.rot_z = 0

    def cleanup(self):
        """Clean up OpenGL resources"""
        if self.isValid():
            self.makeCurrent()
            if self.texture:
                glDeleteTextures([self.texture])
                self.texture = None
            # Note: gluDeleteQuadric doesn't exist in PyOpenGL, quadrics are cleaned up automatically
            self.quadric = None
