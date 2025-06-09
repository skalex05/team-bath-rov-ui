from typing import Literal, TYPE_CHECKING, Callable

from PyQt6.QtCore import QObject, pyqtSignal, QThread

from datainterface.sock_stream_send import SockStreamSend

if TYPE_CHECKING:
    from app import App


# This is a Qt wrapper for SockStreamSend
# It functions almost identically but one must connect to Signals to interface with this object
class QSockStreamSend(QObject):
    on_recv = pyqtSignal(bytes)
    on_connect = pyqtSignal()
    on_disconnect = pyqtSignal()
    on_status_change = pyqtSignal()

    def __init__(self, app: "App", addr: str, port: int, get_data: Callable, sleep: float = 0,
                 protocol: Literal["tcp", "udp"] = "tcp"):
        super().__init__()
        self.send = SockStreamSend(app, addr, port, sleep, get_data,
                                   self.on_connect.emit,
                                   self.on_disconnect.emit,
                                   self.on_status_change.emit,
                                   protocol)
        self.send.start()

        # Place this object in a QThread so that it's signals are not processed by another Thread
        self.thread_container = QThread()
        self.moveToThread(self.thread_container)

    def start(self):
        self.thread_container.start()

    # Used to join the receiver to the main thread.
    def wait(self, timeout: int = 10):
        self.thread_container.wait(timeout)

    def is_connected(self):
        return self.send.is_connected()