from PyQt6.QtCore import QObject, pyqtSignal
from PyQt6.QtGui import QPixmap
from PyQt6.QtWidgets import QLabel

from datainterface.video_frame import VideoFrame


# This class is used to generate a pixmap for a given UI label.
# The UI can connect to the pixmap_ready signal to update the pixmap displayed on a label.

class VideoDisplay(QObject):
    pixmap_ready = pyqtSignal(QPixmap)
    on_disconnect = pyqtSignal()

    def __init__(self, label: QLabel):
        self.label = label
        self.camera_feed: VideoFrame | None = None

        super().__init__()

    def attach_camera_feed(self, camera_feed: VideoFrame) -> None:
        # Remove any old connections to the new frame signal if reattaching camera feed
        if self.camera_feed:
            self.camera_feed.new_frame.disconnect(self.update_frame)
        self.camera_feed = camera_feed
        # Create a new connection to the current camera feed when a new frame is available.
        self.camera_feed.new_frame.connect(self.update_frame)
        self.on_disconnect.emit()

    def update_frame(self) -> None:
        if self.camera_feed is None:
            raise AttributeError("A Camera Feed Is Not Attached")
        # Wait until VideoFrame is free
        with self.camera_feed.lock:
            frame = self.camera_feed.frame
            if frame is not None:
                # Generate the pixmap that will put onto a label
                rect = self.label.geometry()
                pixmap = QPixmap(frame.copy())
                # Ensure image fits available space as best as possible.
                if rect.width() < rect.height():
                    pixmap = pixmap.scaledToWidth(rect.width())
                else:
                    pixmap = pixmap.scaledToHeight(rect.height())
                # Emit signal so that a connected label can update their pixmap.
                self.pixmap_ready.emit(pixmap)
            else:
                # Video feed has disconnected if frame is None
                self.on_disconnect.emit()
