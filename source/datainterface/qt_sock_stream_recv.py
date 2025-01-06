from PyQt6.QtCore import QObject, pyqtSignal, QThread

from datainterface.sock_stream_recv import SockStreamRecv


# This is a Qt wrapper for SockStreamRecv
# It functions almost identically but one must connect to Signals to interface with this object
class QSockStreamRecv(QObject):
    on_recv = pyqtSignal(bytes)
    on_connect = pyqtSignal()
    on_disconnect = pyqtSignal()

    def __init__(self, app, addr, port, buffer_size=1024, protocol="tcp"):
        super().__init__()
        self.recv = SockStreamRecv(app, addr, port, self.on_recv.emit, self.on_connect.emit, self.on_disconnect.emit,
                                   buffer_size, protocol)
        self.recv.start()

        # Place this object in a QThread so that it's signals are not processed by another Thread
        self.thread_container = QThread()
        self.moveToThread(self.thread_container)

    def start(self):
        self.thread_container.start()

    # Used to join the receiver to the main thread.
    def wait(self, timeout=10):
        self.thread_container.wait(timeout)

    def is_connected(self):
        return self.recv.is_connected()
