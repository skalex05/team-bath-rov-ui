import os

from PyQt6.QtCore import QThread
from PyQt6.QtWidgets import QLabel, QProgressBar, QFrame

from datainterface.video_display import VideoDisplay
from datainterface.data_interface import DataInterface
from window import Window

path_dir = os.path.dirname(os.path.realpath(__file__))


def update_pixmap(label, pixmap):
    label.setPixmap(pixmap)


def display_disconnect(label, text):
    label.setText(text)


class Pilot(Window):
    def __init__(self, *args):
        super().__init__(os.path.join(path_dir, "pilot3.ui"), *args)

        self.video_handler_thread = None
        self.data: DataInterface | None = None

        # Setup Camera Feeds

        self.cam_displays = []

        self.main_cam: QLabel = self.findChild(QLabel, "MainCameraView")
        self.secondary_1_cam: QLabel = self.findChild(QLabel, "SecondaryCameraView1")
        self.secondary_2_cam: QLabel = self.findChild(QLabel, "SecondaryCameraView2")

        self.video_handler_thread = QThread()
        for name, cam in zip(["Main Camera", "Secondary Camera 1", "Secondary Camera 2"],
                             [self.main_cam, self.secondary_1_cam, self.secondary_2_cam]):

            # Create Video Display and connect to signals
            display = VideoDisplay(cam)
            display.pixmap_ready.connect(lambda pixmap, _cam=cam: _cam.setPixmap(pixmap))
            display.on_disconnect.connect(lambda _cam=cam, _name=name: _cam.setText(f"{_name} Disconnected"))

            # Move video processing to a separate thread
            display.moveToThread(self.video_handler_thread)
            self.cam_displays.append(display)

        # Tasks

        self.current_title: QLabel = self.findChild(QLabel, "CurrentTitle")
        self.description: QLabel = self.findChild(QLabel, "Description")
        self.up_next_title: QLabel = self.findChild(QLabel, "UpNextTitle")
        self.complete_by_label: QLabel = self.findChild(QLabel, "CompleteBy")
        self.on_task_change()

        self.rpb_perc: QLabel = self.findChild(QLabel, "rpb_perc")
        self.rpb_kpa: QLabel = self.findChild(QLabel, "rpb_kpa")
        self.rpb_path: QFrame = self.findChild(QFrame, "RPB_PATH")

        self.temp_value: QLabel = self.findChild(QLabel, "temp_value")
        self.progressTempBar = self.findChild(QProgressBar, "temp_bar")
        self.progressTempBar.setMinimum(20)
        self.progressTempBar.setMaximum(30)

        self.app.task_checked.connect(self.on_task_change)

    def attach_data_interface(self):
        self.data = self.app.data_interface
        self.data.rov_data_update.connect(self.rpb_sync)
        self.data.rov_data_update.connect(self.temp_sync)

        # Attach camera feeds to respective VideoDisplay objects
        for display, feed in zip(self.cam_displays, self.data.camera_feeds):
            display.attach_camera_feed(feed)

        self.video_handler_thread.start()

    def on_task_change(self):
        # Find out which tasks need to be displayed.
        # Current and next tasks are not necessarily contiguous
        # Also no guarantee there is a current/next task
        current = None
        up_next = None

        for task in self.app.tasks:
            if not task.completed:
                if current is None:
                    current = task
                else:
                    up_next = task
                    break
        if current:
            self.current_title.setText(current.title)
            self.description.setText(current.description)
        else:
            # If there's no current task, all tasks are complete
            self.current_title.setText("All Tasks Complete")
            self.description.setText("Congratulations!")
            self.up_next_title.setText("")
            self.complete_by_label.setText("")
        # Display next task if applicable
        if up_next:
            self.up_next_title.setText(up_next.title)
            self.complete_by_label.setText(f"Complete By: {up_next.start_time[0]:02} : {up_next.start_time[1]:02}")
        else:
            self.up_next_title.setText("")
            self.complete_by_label.setText("")

    def rpb_sync(self):
        # Gauge angle indicates the angle from 0 to 100%
        gauge_angle = 330

        value_kpa = self.data.ambient_pressure
        if not self.data.is_rov_connected():
            value_perc = 0
            value_kpa = 0
        else:
            value_perc = (value_kpa - 100) / 50

        # Update stylesheet to show the new gauge value
        val1 = (1 - value_perc * gauge_angle / 360)
        value1 = val1 - 0.001
        self.rpb_path.setStyleSheet(f"""
        #RPB_PATH{{
            background-color: qconicalgradient(cx:0.5, cy:0.5, angle: {270 - (360 - gauge_angle) / 2}, stop:{val1} rgba(85, 255, 255, 255), stop:{value1} rgba(0, 0, 124, 255));
        }}
        """)
        self.rpb_perc.setText(f"{round(value_perc * 100)}{'%'}")
        self.rpb_kpa.setText(f"{round(value_kpa)}{' kPa'}")

    def temp_sync(self):
        value_temp = self.data.ambient_temperature
        self.progressTempBar.setValue(int(value_temp))
        self.temp_value.setText(f"{round(value_temp)}{'°'}")
