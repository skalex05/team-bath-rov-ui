from PyQt6.QtWidgets import QWidget, QCheckBox, QLabel
from PyQt6 import uic
import os


class Task(QWidget):
    def __init__(self, app, title: str, description: str, start_time: tuple = (0, 0,)):
        super().__init__()
        uic.loadUi(os.path.join("tasks", "task_widget.ui"), self)

        self.checkbox: QCheckBox = self.findChild(QCheckBox, "CheckBox")
        self.start_time_label: QLabel = self.findChild(QLabel, "StartTime")

        self.title = title
        self.description = description
        self.start_time = start_time  # Time will be represented simply as a tuple (mm, ss)
        self.completed = False

        self.app = app

        self.checkbox.clicked.connect(self.on_check)

    def __setattr__(self, key, value):
        if key == "title":
            self.checkbox.setText(value)
        elif key == "completed":
            self.checkbox.setChecked(value)
        elif key == "start_time":
            if type(value) != tuple or len(value) != 2:
                raise ValueError("Start time must be a tuple of 2 integers. (mm, ss)")
            self.start_time_label.setText(f"{value[0]:02} : {value[1]:02}")
        self.__dict__[key] = value

    def on_check(self):
        self.completed = not self.completed
        self.app.task_checked.emit(self)



