import sys
from io import StringIO, TextIOWrapper

from threading import ThreadError
from typing import Union

from PyQt6.QtCore import pyqtSignal, QThread

from copilot.copilot import Copilot
from datainterface.data_interface import DataInterface
from dock import Dock
from grapher.grapher import Grapher
from pilot.pilot import Pilot
from tasks.task import Task

from PyQt6.QtWidgets import QApplication, QWidget

from window import Window


class App(QApplication):
    """
        Class for storing about the overall application.
    """
    task_checked = pyqtSignal(QWidget)

    def __init__(self,
                 redirect_stdout: Union[StringIO, TextIOWrapper],
                 redirect_stderr: Union[StringIO, TextIOWrapper],
                 argv,
                 local_test=True,
                 use_new_camera_system=True,
                 rov_ip="localhost",
                 float_ip="localhost"):
        self.redirect_stdout = redirect_stdout
        self.redirect_stderr = redirect_stderr

        self.use_new_camera_system = use_new_camera_system
        self.local_test = local_test
        if local_test:
            self.UI_IP = "localhost"
            self.ROV_IP = "localhost"
            self.FLOAT_IP = "localhost"
        else:
            self.UI_IP = "0.0.0.0"
            self.ROV_IP = rov_ip
            self.FLOAT_IP = float_ip

        super().__init__(argv)
        self.closing = False

        # TEMPORARY FOR PROCESS SIMULATION
        self.float_data_source_proc = None

        # Create the list of tasks the ROV should complete

        self.tasks: list[Task] = [
            Task(self, "Install AUV docking station", "Move the ROV around and get used to the controls"),
            Task(self, "Place probiotic irrigation system in designated location",
                 "Here is another task that you need to do!", (2, 30)),
            Task(self, "Swim in a cirlce", "Sounds fun!", (3, 30)),
            Task(self, "Produce model of the shipwreck", "Sounds fun!", (5, 45)),
            Task(self, "Do a backflip", "Hell yeah!", (8, 30)),
            Task(self, "Perform a magic trick", "", (10, 10)),
            Task(self, "Deploy the MATE float and move it to the required location", "Nice", (11, 30)),
            Task(self, "Recieve the first set of readings for submersion", "Cool This is very interesting stuff",
                 (12, 0)),
            Task(self, "Recieve the second set of readings for submersion", "Cool This is very interesting stuff",
                 (13, 30)),
            Task(self, "Return to the surface", "Rahhhh", (13, 0)),
            Task(self, "Return to base", "Quickly!", (14, 0))
        ]
        self.tasks = list(sorted(self.tasks, key=lambda t: t.start_time[0] * 60 + t.start_time[1], reverse=True))

        # Get all monitors connected to the computer

        # Assign each window to its own monitor if available
        pilot_monitor = 0
        copilot_monitor = 0
        graph_monitor = 0
        if len(self.screens()) > 1:
            copilot_monitor = 1
            graph_monitor = 1
        if len(self.screens()) > 2:
            graph_monitor = 2

        # Build the dock container

        self.dock = Dock(self, self.screens()[copilot_monitor])

        # Create windows

        self.copilot_window = Copilot(self, self.screens()[copilot_monitor])
        self.pilot_window = Pilot(self, self.screens()[pilot_monitor])
        self.grapher_window = Grapher(self, self.screens()[graph_monitor])

        # Attach the navigation bars to these windows

        self.copilot_window.attach_nav_bar(self.dock)
        self.pilot_window.attach_nav_bar(self.dock)
        self.grapher_window.attach_nav_bar(self.dock)

        # Add windows to the dock
        self.dock.add_windows(self.copilot_window, self.pilot_window, self.grapher_window)

        # Undock windows if extra monitors are available
        if len(self.screens()) > 1:
            self.pilot_window.nav.f_undock()

        if len(self.screens()) > 2:
            self.grapher_window.nav.f_undock()

        self.dock.showFullScreen()
        current_window: Window = self.dock.currentWidget()
        current_window.nav.clear_layout()
        current_window.nav.generate_layout()

        windows: list[Window] = [self.copilot_window, self.pilot_window, self.grapher_window]
        # Create the data interface
        # Local redirected stdout/stderr should be passed so that it can be processed in this thread.
        self.data_interface_thread = QThread()
        self.data_interface: DataInterface = DataInterface(self, windows, redirect_stdout, redirect_stderr)
        self.data_interface.moveToThread(self.data_interface_thread)
        self.data_interface_thread.start()

        # Connect windows to data interface signals
        for window in windows:
            window.attach_data_interface()

        # Initially set the rov/float to be disconnected
        self.data_interface.rov_data_thread.on_disconnect.emit()
        self.data_interface.float_data_thread.on_disconnect.emit()

        dark_theme = """
            Window {
                background-color:rgb(30,30,30);
            }

            QScrollArea#TaskList {
                background-color:rgb(50,50,50);
                color: white;
            }
            QWidget#TaskListContents {
                background-color:rgb(50,50,50);
                color: white;

            }
            QFrame {
                background-color:rgb(30,30,30);
                color: white;

            }
            QLabel {
                color: white;
            }
            QPlainTextEdit#Stdout {
                background-color:rgb(50,50,50);
                color: white;
            }
            QRadioButton {
                color:white;
            }
        """
        self.setStyleSheet(dark_theme)

        if not local_test:
            print("Note: RUN_ROV_LOCALLY is set to False in main.py - Only use this when testing with the "
                  "Raspberry Pi or for production")

    def reset_task_completion(self) -> None:
        for task in self.tasks:
            task.completed = False

    def close(self) -> None:
        if self.closing:
            return
        self.closing = True
        print("Closing", file=sys.__stdout__, flush=True)
        # Close dummy processes
        if self.float_data_source_proc:
            print("Attempting to close Float data source", file=sys.__stdout__, flush=True)
            try:
                self.float_data_source_proc.terminate()
                print("Killed float data source", file=sys.__stdout__, flush=True)
            except Exception as e:
                print("Couldn't kill float data source - ", e, file=sys.__stdout__, flush=True)
        # Rejoin threads before closing
        try:
            self.data_interface.close()
            print("Closing data interface threads", file=sys.__stdout__, flush=True)
        except ThreadError as e:
            print("Could not close data interface threads.", file=sys.__stdout__, flush=True)
        self.quit()
