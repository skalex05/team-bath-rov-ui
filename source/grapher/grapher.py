import os
import sys
import shutil
import time
from pathlib import Path

import cv2
import pandas as pd
from PyQt6.QtCore import QThreadPool, QUrl, Qt, QSizeF, QTimer, QFileSystemWatcher, pyqtSignal
from PyQt6.QtMultimediaWidgets import QGraphicsVideoItem

from PyQt6.QtWidgets import QApplication, QVBoxLayout, QPushButton, QLineEdit, QMessageBox, QLabel, QTabWidget, \
    QFileDialog, QProgressBar, QTableWidget, QTableWidgetItem, QGraphicsView, QGraphicsScene, QFrame, QInputDialog, \
    QCheckBox, QComboBox
from PyQt6.QtGui import QIcon
from PyQt6.QtMultimedia import QMediaPlayer

from matplotlib.backends.backend_qtagg import NavigationToolbar2QT as NavigationToolbar

from grapher.graph_widget import GraphWidget
from grapher.multi_combo_box import MultiSelectComboBox
from rov_float_data_structures.float_data import FloatData
from rov_float_data_structures.rov_data import ROVData
from data_classes.vector3 import Vector3 as Vector3
from grapher.graphGenerator import GraphGenerator

from graphing_task import GraphingTask
from grapher.eDNASampler import eDNASampler
from nav_bar.nav_bar import NavBar

from window import Window

path_dir = os.path.dirname(os.path.realpath(__file__))


class Grapher(Window):
    recording_update = pyqtSignal()
    recording_end = pyqtSignal()

    def __init__(self, *args):
        super().__init__(os.path.join(path_dir, "grapher.ui"), *args)

        # General Attributes
        self.tab_widget: QTabWidget = self.findChild(QTabWidget, "TabWidget")

        # Graph Creator Attributes
        self.graph_generator = GraphGenerator()  # From graphGenerator.py
        self.toolbar = None
        self.generating_model = False
        self.displaying_no_graph_tab = False

        self.GraphTabWidget: QTabWidget = self.findChild(QTabWidget, "Graphs")
        self.GraphTabWidget.tabCloseRequested.connect(self.graph_closed)
        while self.GraphTabWidget.count() > 0:
            self.GraphTabWidget.removeTab(0)
        self.graph_closed()

        self.RecordedFieldsContainer: QFrame = self.findChild(QFrame, "RecordedFieldsContainer")
        self.RecordedFieldsLabel: QLabel = self.findChild(QLabel, "SelectedFieldsLabel")

        self.StartRecordingButton: QPushButton = self.findChild(QPushButton, "StartRecording")
        self.StartRecordingButton.clicked.connect(self.toggle_recording)

        self.InputRecordingContainer: QFrame = self.findChild(QFrame, "InputRecordingContainer")
        self.InputRecording: QComboBox = self.findChild(QComboBox, "InputRecording")
        self.InputRecording.currentTextChanged.connect(self.display_field_axes_options)

        self.LiveGraph: QCheckBox = self.findChild(QCheckBox, "LiveGraph")
        self.LiveGraph.setEnabled(False)
        def live_graph_change(state):
            if state == Qt.CheckState.Checked:
                self.InputRecordingContainer.hide()
            else:
                self.InputRecordingContainer.show()

            self.display_field_axes_options()

        self.LiveGraph.checkStateChanged.connect(live_graph_change)

        self.XAxisSelector: QFrame = self.findChild(QFrame, "XAxisSelector")
        self.XAxis: QComboBox = self.findChild(QComboBox, "XAxis")
        self.YAxisSelector: QFrame = self.findChild(QFrame, "YAxisSelector")
        self.YAxis: QComboBox = self.findChild(QComboBox, "YAxis")
        self.ZAxisSelector: QFrame = self.findChild(QFrame, "ZAxisSelector")
        self.ZAxis: QComboBox = self.findChild(QComboBox, "ZAxis")

        self.GraphType: QComboBox = self.findChild(QComboBox, "GraphType")
        self.GraphType.currentTextChanged.connect(
            lambda text: self.ZAxisSelector.show() if text == "3D Graph" else self.ZAxisSelector.hide())
        self.GraphType.setCurrentText("2D Graph")

        self.CreateGraphButton: QPushButton = self.findChild(QPushButton, "CreateNewGraph")
        self.CreateGraphButton.clicked.connect(self.create_graph)

        self.is_recording = False
        self.recording_file_path = ""
        self.recording_dataframe: pd.DataFrame = None
        self.fields_to_record = []
        self.recording_timer = QTimer()
        self.recording_timer.timeout.connect(self.record_fields)
        self.recordings_path = Path(os.getcwd()) / "Recordings"

        self.on_recording_directory_changed()

        if not self.recordings_path.exists():
            os.mkdir(self.recordings_path)

        self.watcher = QFileSystemWatcher()
        self.watcher.addPath(str(self.recordings_path))
        self.watcher.directoryChanged.connect(self.on_recording_directory_changed)

        fields = []
        rov_data_obj = ROVData()
        for attr in rov_data_obj.__dict__:
            val = getattr(rov_data_obj, attr)
            if type(val) is Vector3:
                fields.append(attr + ".x")
                fields.append(attr + ".y")
                fields.append(attr + ".z")
            else:
                fields.append(attr)

        float_data_obj = FloatData()
        for attr in float_data_obj.__dict__:
            val = getattr(float_data_obj, attr)
            if type(val) == Vector3:
                fields.append(attr + ".x")
                fields.append(attr + ".y")
                fields.append(attr + ".z")
            else:
                fields.append(attr)

        self.RecordedFields = MultiSelectComboBox(self.RecordedFieldsLabel)
        self.RecordedFieldsContainer.layout().addWidget(self.RecordedFields)
        self.RecordedFields.on_item_select.connect(self.display_field_axes_options)

        self.recordable_fields = {}

        for field in fields:
            pretty_field = field.replace("_", " ").replace(".", " ").title()
            self.recordable_fields[pretty_field] = field
            self.RecordedFields.addItem(pretty_field, userData=field)

        # eDNA Attributes
        self.eDNA_database = None
        self.unknown_sample_folder = None

        self.eDNAResults: QTableWidget = self.findChild(QTableWidget, "eDNAResults")

        self.eDNAButton: QPushButton = self.findChild(QPushButton, "eDNAButton")
        self.eDNAButton.clicked.connect(self.on_eDNA_clicked)

        self.eDNADatabaseSelect: QPushButton = self.findChild(QPushButton, "eDNADatabaseSelect")
        self.eDNADatabaseSelect.clicked.connect(
            lambda: self.select_eDNA_path("eDNA_database", "eDNADatabasePath", "Choose A Folder of Known eDNA Samples"))

        self.eDNADatabasePath = self.findChild(QLabel, "eDNADatabasePath")

        self.UnknownSampleFolderSelect = self.findChild(QPushButton, "UnknownSampleFolderSelect")
        self.UnknownSampleFolderSelect.clicked.connect(
            lambda: self.select_eDNA_path("unknown_sample_folder", "UnknownSampleFolderPath",
                                          "Choose A Folder of Unknown eDNA Samples"))

        self.UnknownSampleFolderPath = self.findChild(QLabel, "UnknownSampleFolderPath")

        self.eDNAProgressBar: QProgressBar = self.findChild(QProgressBar, "eDNAProgress")

        self.eDNA_sampler = eDNASampler()
        self.eDNA_sampler.progress_update.connect(lambda pi: self.eDNAProgressBar.setValue(pi))

        # Migration Attributes
        self.area1 = self.findChild(QLineEdit, "Area1Year")
        self.area2 = self.findChild(QLineEdit, "Area2Year")
        self.area3 = self.findChild(QLineEdit, "Area3Year")
        self.area4 = self.findChild(QLineEdit, "Area4Year")
        self.area5 = self.findChild(QLineEdit, "Area5Year")

        self.MigrationModelButton = self.findChild(QPushButton, "MigrationModelButton")
        self.MigrationModelButton.clicked.connect(self.on_generate_model_clicked)

        self.VideoContainer: QGraphicsView = self.findChild(QGraphicsView, "VideoContainer")
        self.VideoContainer.mousePressEvent = lambda event: self.play_migration_video()

        self.migration_media_player = QMediaPlayer()
        self.migration_video_item = QGraphicsVideoItem()
        self.migration_media_player.setVideoOutput(self.migration_video_item)

        scene = QGraphicsScene()
        scene.addItem(self.migration_video_item)

        self.VideoContainer.setScene(scene)

    def attach_nav_bar(self, dock) -> None:
        tab_bar = self.tab_widget.tabBar()
        width = 0
        for i in range(tab_bar.count()):
            width += tab_bar.tabRect(i).width()
        self.nav = NavBar(self, dock, nav_bar_right_offset=width)
        self.nav.generate_layout()

    def on_recording_directory_changed(self):
        while self.InputRecording.count() > 0:
            self.InputRecording.removeItem(0)
        for file in os.listdir(self.recordings_path):
            self.InputRecording.addItem(file)

    def record_fields(self):
        new_row = [time.time()]
        for pretty_field in self.fields_to_record:
            field = self.recordable_fields[pretty_field]
            attrs = field.split(".")
            attr = self.data
            if len(attrs) > 1:
                for i in range(len(attrs)-1):
                    attr = getattr(attr, attrs[i])
            data = getattr(attr, attrs[-1])
            new_row.append(data)
        try:
            with open(self.recording_file_path, "a") as f:
                text = ",".join([str(f) for f in new_row])+"\n"
                f.write(text)
        except Exception as e:
            self.toggle_recording()
            QMessageBox.warning(None, "Error", f"Recording Failed Unexpectedly:\n{e}")

        self.recording_dataframe.loc[len(self.recording_dataframe)] = new_row

        self.recording_update.emit()

    def display_field_axes_options(self):
        if self.LiveGraph.isChecked() and self.is_recording:
            fields = ["Time"]+self.fields_to_record
        else:
            selected_file = self.recordings_path/self.InputRecording.currentText()
            if selected_file == "":
                return
            try:
                df = pd.read_csv(selected_file)
                fields = list(df.columns)
            except Exception as e:
                print(e, file=sys.stderr)
                return
        x_axis_choice = self.XAxis.currentText()
        y_axis_choice = self.YAxis.currentText()
        z_axis_choice = self.ZAxis.currentText()

        while self.XAxis.count() > 0:
            self.XAxis.removeItem(0)
        for field in fields:
            self.XAxis.addItem(field)
        if x_axis_choice in fields:
            self.XAxis.setCurrentText(x_axis_choice)

        while self.YAxis.count() > 0:
            self.YAxis.removeItem(0)
        for field in fields:
            self.YAxis.addItem(field)
        if y_axis_choice in fields:
            self.YAxis.setCurrentText(y_axis_choice)

        while self.ZAxis.count() > 0:
            self.ZAxis.removeItem(0)
        for field in fields:
            self.ZAxis.addItem(field)
        if z_axis_choice in fields:
            self.ZAxis.setCurrentText(z_axis_choice)


    def toggle_recording(self):
        if not self.is_recording:
            selected_fields = self.RecordedFields.get_selected()
            if len(selected_fields) == 0:
                QMessageBox.warning(self, "No Field Selected", f"Please select at least one field to record")
                return

            filename, ok = QInputDialog.getText(None, "Recording Filename", "Enter a filename for the recording: ")
            if not ok:
                return

            new_recording = self.recordings_path / f"{filename}.csv"
            if new_recording.exists():
                response = QMessageBox.warning(None,
                                               "File Exists",
                                               f"A recording called {filename} already exists. "
                                               f"Would you like to overwrite it?",
                                               QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                                               QMessageBox.StandardButton.No
                                               )
                if response == QMessageBox.StandardButton.No:
                    return

            self.recording_file_path = new_recording
            self.recording_dataframe = pd.DataFrame([], columns=["Time"] + selected_fields)
            self.fields_to_record = selected_fields

            try:
                with open(self.recording_file_path, "w+") as f:
                    f.write(",".join(self.recording_dataframe.columns)+"\n")
            except Exception as e:
                QMessageBox.warning(None, "Error", f"Failed to start recording:\n{e}")
                return

            self.StartRecordingButton.setText("Stop Recording")
            self.RecordedFields.hide()
            self.recording_timer.start(100)
            self.is_recording = True
            self.LiveGraph.setEnabled(True)
            self.LiveGraph.setChecked(False)

            self.display_field_axes_options()
        else:
            self.StartRecordingButton.setText("Start Recording")
            self.RecordedFields.show()
            self.recording_timer.stop()
            self.is_recording = False
            self.LiveGraph.setEnabled(False)
            self.LiveGraph.setChecked(False)
            self.recording_end.emit()

    def create_graph(self):
        axes = [self.XAxis.currentText(), self.YAxis.currentText()]
        if self.GraphType.currentText() == "3D Graph":
            axes.append(self.ZAxis.currentText())
        if any([axis == "" for axis in axes]):
            QMessageBox.warning(None, "Empty Axis", "Please set fields for each axis for the graph")
            return

        title, ok = QInputDialog.getText(None, "Figure Title", "Enter a title for the figure: ")
        if not ok:
            return

        if self.LiveGraph.isChecked():
            graph_widget = GraphWidget(self.recording_dataframe, axes,  self.GraphType.currentText() == "3D Graph",
                                       True, title,
                                       recording_update_signal=self.recording_update,
                                       recording_end_signal=self.recording_end)
        else:
            df_file = self.InputRecording.currentText()
            if df_file == "":
                QMessageBox.warning(None, "No Chosen Recording", "Please select a recording to graph")
                return

            df = pd.read_csv(self.recordings_path/df_file)
            graph_widget = GraphWidget(df, axes, self.GraphType.currentText() == "3D Graph", False, title)

        if not graph_widget.build_success:
            return

        if self.displaying_no_graph_tab:
            self.displaying_no_graph_tab = False
            self.GraphTabWidget.removeTab(0)

        self.GraphTabWidget.addTab(graph_widget, title)
        self.GraphTabWidget.setCurrentWidget(graph_widget)

    def graph_closed(self):
        if self.GraphTabWidget.count() == 0:
            self.displaying_no_graph_tab = True
            no_graphs_label = QLabel("No Graphs to Display...")
            no_graphs_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.GraphTabWidget.addTab(no_graphs_label, "No Graphs to Display")


    def model_migration(self, start_year: int, end_year: int, migration_years: list[int], input_images: list[str],
                        year_display_positions: list[tuple[int, int]]):
        self.migration_media_player.stop()
        if self.generating_model:
            return
        self.generating_model = True
        assert len(migration_years) == 5 and len(input_images) == 6 and len(year_display_positions) == 6

        # Remove Frames folder and contents

        if os.path.exists("Frames"):
            shutil.rmtree("Frames")
        if not os.path.exists("Frames"):
            os.mkdir("Frames")
        else:
            raise OSError("Failed to remove Frames folder")
        if not os.path.exists("Frames"):
            raise OSError("Failed to recreate Frames folder")

        font = cv2.FONT_HERSHEY_SIMPLEX
        font_scale = 1.5
        color = (0, 0, 255)
        thickness = 5

        # Generate Frames

        current_migration = 0
        for i, year in enumerate(range(start_year, end_year + 1)):
            # Progress carp migration until end
            while current_migration < 5 and migration_years[current_migration] is not None and year >= migration_years[
                current_migration]:
                current_migration += 1

            frame = cv2.imread(input_images[current_migration])
            if frame is None:
                raise ValueError(f"Could not read file: {input_images[current_migration]}")

            cv2.putText(frame, str(year), year_display_positions[current_migration], font, font_scale, color, thickness,
                        cv2.LINE_AA)

            cv2.imwrite(f"Frames\\{i:04}.jpg", frame)

        # Create Video
        print("Creating video", file=sys.__stdout__, flush=True)
        os.system(f"ffmpeg -y -framerate 1 -i Frames\\%4d.jpg migration.mp4 -start_number 0 -vf format=yuv420")

        self.generating_model = False

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.migration_video_item.setSize(QSizeF(self.VideoContainer.width(), self.VideoContainer.height()))
        self.VideoContainer.scene().setSceneRect(self.migration_video_item.boundingRect())
        self.VideoContainer.fitInView(self.migration_video_item, Qt.AspectRatioMode.KeepAspectRatio)

    def on_generate_model_clicked(self):
        start_year = 2016
        end_year = 2025

        sanitised_years = []
        # Ensure inputted values are either valid years or left blank
        for v in [self.area1, self.area2, self.area3, self.area4, self.area5]:
            v = v.text()
            if v == "":
                sanitised_years.append(None)
                continue
            if not v.isdigit():
                return
            v = int(v)
            if v < start_year or v > end_year:
                return
            sanitised_years.append(v)

        task = GraphingTask(lambda: self.model_migration(start_year, end_year,
                                                         sanitised_years,
                                                         [
                                                             r"Migration Images\Area0.png",
                                                             r"Migration Images\Area1.png",
                                                             r"Migration Images\Area2.png",
                                                             r"Migration Images\Area3.png",
                                                             r"Migration Images\Area4.png",
                                                             r"Migration Images\Area5.png",
                                                         ],
                                                         [
                                                             (70, 830),
                                                             (240, 620),
                                                             (340, 450),
                                                             (440, 380),
                                                             (650, 280),
                                                             (750, 180),
                                                         ]),
                            self.play_migration_video)

        QThreadPool.globalInstance().start(task)

    def play_migration_video(self, callback_in=None):
        video = QUrl.fromLocalFile(f"{os.getcwd()}\\migration.mp4")

        self.migration_media_player.stop()
        self.migration_media_player.setSource(QUrl())

        self.migration_media_player.setSource(video)
        self.migration_media_player.setLoops(QMediaPlayer.Loops.Infinite)

        self.migration_video_item.setSize(QSizeF(self.VideoContainer.width(), self.VideoContainer.height()))
        self.VideoContainer.scene().setSceneRect(self.migration_video_item.boundingRect())
        self.VideoContainer.fitInView(self.migration_video_item, Qt.AspectRatioMode.KeepAspectRatio)

        self.migration_media_player.play()

    def on_velocity_dropdown_clicked(self):
        '''Toggle visibility of velocity checkboxes when vel button pressed'''
        visible = not self.velocityX.isVisible()
        for attr in ["velocityX", "velocityY", "velocityZ"]:
            checkbox = getattr(self, attr, None)
            if checkbox:
                checkbox.setVisible(visible)

    def on_acceleration_dropdown_clicked(self):
        '''Toggle visibility of accel checkboxes when acceleration button pressed'''
        visible = not self.accelerationX.isVisible()
        for attr in ["accelerationX", "accelerationY", "accelerationZ"]:
            checkbox = getattr(self, attr, None)
            if checkbox:
                checkbox.setVisible(visible)

    def on_velocity_clicked(self):
        """Generate velocity plot."""  # for now showing acceleration as placeholder, just integrate data in graphGen for v
        packet_number, accel_x, accel_y, accel_z = self.graph_generator.read_data()

        # Checking which velocity axes are to be used
        x = accel_x if getattr(self, "velocityX", None) and self.velocityX.isChecked() else None
        y = accel_y if getattr(self, "velocityY", None) and self.velocityY.isChecked() else None
        z = accel_z if getattr(self, "velocityZ", None) and self.velocityZ.isChecked() else None

        if x is None and y is None and z is None:
            print("Error: No velocity components selected!")
            return

        print(f"Selected Data for Plotting: X={x}, Y={y}, Z={z}")

        # Generating graph
        self.graph_generator.generate_acceleration(self.graphArea, packet_number, x, y, z, save_path="velocity.png")
        self.update_button_icon("velocityButton", "velocity.png")
        self.add_toolbar(self.graph_generator.canvas)

    def on_acceleration_clicked(self):
        """Generate acceleration plot."""
        packet_number, accel_x, accel_y, accel_z = self.graph_generator.read_data()

        # Checking which acceleration axes are to be used
        x = accel_x if getattr(self, "accelerationX", None) and self.accelerationX.isChecked() else None
        y = accel_y if getattr(self, "accelerationY", None) and self.accelerationY.isChecked() else None
        z = accel_z if getattr(self, "accelerationZ", None) and self.accelerationZ.isChecked() else None

        if x is None and y is None and z is None:
            print("Error: No velocity components selected!")
            return

        print(f"Selected Data for Plotting: X={x}, Y={y}, Z={z}")

        # graphing
        self.graph_generator.generate_acceleration(self.graphArea, packet_number, x, y, z, save_path="acceleration.png")
        self.update_button_icon("accelerationButton", "acceleration.png")
        self.add_toolbar(self.graph_generator.canvas)

    def on_depth_clicked(self):
        """Generate depth plot."""
        try:  # It kept crashing, so I added this. It's working now
            print("Depth button clicked.")

            # Read data from the same function as before
            packet_number, accel_x, accel_y, accel_z = self.graph_generator.read_data()

            # Packet number is valid?
            if packet_number is None:
                print("Error: No packet number data available!")
                return  # Prevents crash

            print(f"Selected Data for Plotting: Packet Number={packet_number[:10]}")  # Debug first 10 values

            # Generate and display the depth graph (Fix function name to match the new version)
            print("Generating depth graph now...")
            self.graph_generator.generate_depth_plot(self.graphArea, packet_number, accel_x, accel_y, accel_z,
                                                     save_path="depth.png")

            print("Updating button icon and toolbar...")
            self.update_button_icon(self.depthButton, "depth.png")
            self.add_toolbar(self.graph_generator.canvas)

            print("Depth graph successfully displayed.")

        except Exception as e:
            print(f"Unhandled Error in on_depth_clicked: {str(e)}")
            import traceback
            traceback.print_exc()

    def on_eDNA_clicked(self):
        if self.unknown_sample_folder is None or self.eDNA_database is None:
            QMessageBox.warning(self, "Error", f"Please set Unknown Sample and Species Database Folders")
            return
        try:
            def on_task_complete(results):
                for row, (sample_no, score, classification) in enumerate(results):
                    self.eDNAResults.setItem(row, 0, QTableWidgetItem(str(sample_no)))
                    self.eDNAResults.setItem(row, 1, QTableWidgetItem(str(int(score))))
                    self.eDNAResults.setItem(row, 2, QTableWidgetItem(classification))

            task = GraphingTask(
                lambda: self.eDNA_sampler.generate_results(self.unknown_sample_folder, self.eDNA_database),
                on_task_complete)
            QThreadPool.globalInstance().start(task)

        except Exception as e:
            QMessageBox.warning(self, "Error", f"Error in eDNA sampling: {str(e)}")

    def select_eDNA_path(self, dest_attribute: str, dest_label: str, caption: str):
        folder_path = QFileDialog.getExistingDirectory(self, caption)

        if folder_path:
            setattr(self, dest_attribute, folder_path)
            getattr(self, dest_label).setText(str(folder_path))

    def update_button_icon(self, button_name, image_path):
        button = getattr(self, button_name, None)
        if button:
            button.setIcon(QIcon(image_path))
            button.setIconSize(button.size())

    def add_toolbar(self, canvas):
        if self.toolbar is not None:
            self.graphArea.layout().removeWidget(self.toolbar)
            self.toolbar.deleteLater()
            self.toolbar = None

        self.toolbar = NavigationToolbar(canvas, self)
        self.graphArea.layout().addWidget(self.toolbar)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = Grapher()
    window.show()
    sys.exit(app.exec())
