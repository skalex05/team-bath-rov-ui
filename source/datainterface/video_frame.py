from threading import Lock

from PyQt6.QtCore import QObject, pyqtSignal

# A simple class that allows frame data to be locked to a single process
# A new frame is ready why the new_frame signal is raised
class VideoFrame(QObject):
    new_frame = pyqtSignal()

    def __init__(self):
        self.frame = None
        self.lock = Lock()
        super().__init__()
