import time
from typing import Literal, TYPE_CHECKING

from PyQt6.QtCore import QObject, pyqtSignal, QThread

from threading import Thread
import av
from numpy import ndarray

if TYPE_CHECKING:
    from app import App


# A new class for the new, improved and simplified camera system!
class VideoRecv(QObject):
    on_recv = pyqtSignal(ndarray)
    on_connect = pyqtSignal()
    on_disconnect = pyqtSignal()

    def __init__(self, app: "App", addr: str, port: int):
        print(f"Creating a Camera Receiver: {addr=} {port=}")

        super().__init__()

        def recv():
            while not app.closing:
                time.sleep(0)
                connected = False
                try:
                    with av.open(f"udp://{addr}:{port}?timeout=1000&buffer_size=65536", timeout=1) as container:
                        if app.closing:
                            continue
                        for frame in container.decode(video=0):
                            if app.closing:
                                break

                            if not connected:
                                connected = True
                                self.on_connect.emit()

                            frame = frame.to_ndarray(format="bgr24")

                            self.on_recv.emit(frame)
                except (OSError, av.ExitError) as e:
                    time.sleep(0.5)
                if connected:
                    self.on_disconnect.emit()

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
