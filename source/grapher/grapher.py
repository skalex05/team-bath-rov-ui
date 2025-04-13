import os
import sys
import shutil
import time

import cv2
from PyQt6.QtCore import QThreadPool, QTimer, QRect, QUrl, QFileInfo, Qt, QSizeF
from PyQt6.QtMultimediaWidgets import QVideoWidget, QGraphicsVideoItem

from PyQt6.QtWidgets import QApplication, QVBoxLayout, QPushButton, QLineEdit, QMessageBox, QLabel, QTabWidget, \
    QFileDialog, QProgressBar, QTableWidget, QTableWidgetItem, QFrame, QLayout, QGraphicsView, QGraphicsScene
from PyQt6.QtGui import QIcon, QPainter, QPen
from PyQt6.QtMultimedia import QMediaPlayer

from matplotlib.backends.backend_qtagg import NavigationToolbar2QT as NavigationToolbar
from grapher.graphGenerator import GraphGenerator

from graphing_task import GraphingTask
from grapher.eDNASampler import eDNASampler
from nav_bar.nav_bar import NavBar

from window import Window

path_dir = os.path.dirname(os.path.realpath(__file__))


class Grapher(Window):

    def __init__(self, *args):
        super().__init__(os.path.join(path_dir, "grapher_new.ui"), *args)

        # General Attributes
        self.tab_widget: QTabWidget = self.findChild(QTabWidget, "TabWidget")

        # Graph Creator Attributes
        self.graph_generator = GraphGenerator()  # From graphGenerator.py
        self.toolbar = None
        self.generating_model = False

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

        return

        if self.graphArea.layout() is None:  # Making sure graph area has layout
            self.graphArea.setLayout(QVBoxLayout())

        # Enable checkboxes for vel & acceleration axes
        for attr in ["velocityX", "velocityY", "velocityZ", "accelerationX", "accelerationY", "accelerationZ"]:
            checkbox = getattr(self, attr, None)
            if checkbox:
                checkbox.setChecked(True)

        # Connecting buttons
        self.velocityDropdownButton = self.findChild(QPushButton, "velocityDropdownButton")
        self.velocityDropdownButton.clicked.connect(self.on_velocity_dropdown_clicked)

        self.accelerationDropdownButton = self.findChild(QPushButton, "accelerationDropdownButton")
        self.accelerationDropdownButton.clicked.connect(self.on_acceleration_dropdown_clicked)

        self.velocityButton = self.findChild(QPushButton, "velocityButton")
        self.velocityButton.clicked.connect(self.on_velocity_clicked)

        self.accelerationButton = self.findChild(QPushButton, "accelerationButton")
        self.accelerationButton.clicked.connect(self.on_acceleration_clicked)

        self.depthButton = self.findChild(QPushButton, "depthButton")
        self.depthButton.clicked.connect(self.on_depth_clicked)

    def attach_nav_bar(self, dock) -> None:
        tab_bar = self.tab_widget.tabBar()
        width = 0
        for i in range(tab_bar.count()):
            width += tab_bar.tabRect(i).width()
        self.nav = NavBar(self, dock, nav_bar_right_offset=width)
        self.nav.generate_layout()

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
        print("playing video", file=sys.__stdout__, flush=True)
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

            task = GraphingTask(lambda: self.eDNA_sampler.generate_results(self.unknown_sample_folder, self.eDNA_database), on_task_complete)
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
