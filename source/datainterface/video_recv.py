import sys
from typing import Literal, TYPE_CHECKING

from PyQt6.QtCore import QObject, pyqtSignal, QThread

from threading import Thread
import cv2
from numpy import ndarray

if TYPE_CHECKING:
    from app import App


# A new class for the new, improved and simplified camera system!
class VideoRecv(QObject):
    on_recv = pyqtSignal(ndarray)
    on_connect = pyqtSignal()
    on_disconnect = pyqtSignal()

    def __init__(self, app: "App", addr: str, port: int):
        super().__init__()

        def recv():
            while not app.closing:
                cap = cv2.VideoCapture(f"udp://{addr}:{port}?timeout=1000")
                if app.closing:
                    continue
                if not cap.isOpened():
                    cap.release()
                    continue
                self.on_connect.emit()
                while not app.closing:
                    ret, frame = cap.read()
                    if not ret:
                        self.on_disconnect.emit()
                        cap.release()
                        break

                    self.on_recv.emit(frame)
                cap.release()

        self.thread = Thread(target=recv)
        self.thread.start()

        # Place this object in a QThread so that it's signals are not processed by another Thread
        self.thread_container = QThread()
        self.moveToThread(self.thread_container)

    def start(self):
        self.thread_container.start()

    # Used to join the receiver to the main thread.
    def wait(self, timeout: int = 10):
        self.thread_container.wait(timeout)

    def is_connected(self):
        return self.recv.is_connected()
