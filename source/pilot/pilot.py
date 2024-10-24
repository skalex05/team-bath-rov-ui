import os

from PyQt6.QtWidgets import QLabel

from data_interface.data_interface import DataInterface
from window import Window

path_dir = os.path.dirname(os.path.realpath(__file__))


class Pilot(Window):
    def __init__(self, *args):
        super().__init__(f"{path_dir}\\pilot.ui", *args)

        self.data: DataInterface | None = None

        # Cameras

        self.main_cam: QLabel = self.findChild(QLabel, "MainCameraView")
        self.secondary_1_cam: QLabel = self.findChild(QLabel, "SecondaryCameraView1")
        self.secondary_2_cam: QLabel = self.findChild(QLabel, "SecondaryCameraView2")

        self.cam_info = [
            ("Main Camera", self.main_cam),
            ("Secondary Camera 1", self.secondary_1_cam),
            ("Secondary Camera 2", self.secondary_2_cam),
        ]

        # Tasks

        self.current_title: QLabel = self.findChild(QLabel, "CurrentTitle")
        self.description: QLabel = self.findChild(QLabel, "Description")
        self.up_next_title: QLabel = self.findChild(QLabel, "UpNextTitle")
        self.complete_by_label: QLabel = self.findChild(QLabel, "CompleteBy")
        self.on_task_change()

        self.app.task_checked.connect(self.on_task_change)

    def attach_data_interface(self):
        self.data = self.app.data_interface
        self.data.video_stream_update.connect(self.update_video_data)

    def on_task_change(self):
        # Find out which tasks need to be displayed.
        # Current and next tasks are not necessarily contiguous
        current = None
        up_next = None

        for task in self.app.tasks:
            if not task.completed:
                if current is None:
                    current = task
                else:
                    up_next = task
                    break

        self.current_title.setText(current.title)
        self.description.setText(current.description)
        self.up_next_title.setText(up_next.title)
        self.complete_by_label.setText(f"Complete By: {up_next.start_time[0]:02} : {up_next.start_time[1]:02}")

    def update_video_data(self, i: int):
        cam = self.cam_info[i]
        try:
            frame = self.data.camera_feeds[i]
            if frame.camera_frame:
                rect = cam[1].geometry()
                cam[1].setPixmap(frame.generate_pixmap(rect.width(), rect.height()))
            else:
                raise IndexError()
        except IndexError:
            cam[1].setText(f"{cam[0]} Is Unavailable")

