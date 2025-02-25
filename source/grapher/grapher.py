import os
import sys
import shutil


import cv2
from PyQt6.QtCore import QThreadPool, QTimer

from PyQt6.QtWidgets import QApplication, QVBoxLayout, QPushButton, QLineEdit, QMessageBox, QLabel
from PyQt6.QtGui import QIcon

from matplotlib.backends.backend_qtagg import NavigationToolbar2QT as NavigationToolbar
from grapher.graphGenerator import GraphGenerator

from graphing_task import GraphingTask
from grapher.eDNASampler import eDNASampler

from window import Window

from functools import partial

path_dir = os.path.dirname(os.path.realpath(__file__))

generating_model = False
def model_migration(start_year: int, end_year: int, migration_years: list[int], input_images: list[str],
                    year_display_positions: list[tuple[int, int]]):
    global generating_model
    if generating_model:
        return
    generating_model = True
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

    os.system(f"ffmpeg -y -framerate 1 -i Frames\\%4d.jpg migration.mp4 -start_number 0 -vf format=yuv420")

    generating_model = False


class Grapher(Window):
    def __init__(self, *args):
        super().__init__(os.path.join(path_dir, "grapher.ui"), *args)

        self.graph_generator = GraphGenerator()  # From graphGenerator.py
        self.toolbar = None

        self.eDNA_results: QLabel = self.findChild(QLabel, "eDNA_results")

        if self.graphArea.layout() is None: # Making sure graph area has layout
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

        for child in self.children():
            print(child, file=sys.__stdout__, flush=True)
        self.MigrationModelButton = self.findChild(QPushButton, "MigrationModelButton")
        self.MigrationModelButton.clicked.connect(self.on_generate_model_clicked)

        self.velocityButton = self.findChild(QPushButton, "velocityButton")
        self.velocityButton.clicked.connect(self.on_velocity_clicked)

        self.accelerationButton = self.findChild(QPushButton, "accelerationButton")
        self.accelerationButton.clicked.connect(self.on_acceleration_clicked)

        self.depthButton = self.findChild(QPushButton, "depthButton")
        self.depthButton.clicked.connect(self.on_depth_clicked)

        self.eDNAButton = self.findChild(QPushButton, "eDNAButton")
        self.eDNAButton.clicked.connect(self.on_eDNA_clicked)

        self.area1 = self.findChild(QLineEdit, "Area1Year")
        self.area2 = self.findChild(QLineEdit, "Area2Year")
        self.area3 = self.findChild(QLineEdit, "Area3Year")
        self.area4 = self.findChild(QLineEdit, "Area4Year")
        self.area5 = self.findChild(QLineEdit, "Area5Year")

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

        task = GraphingTask(lambda: model_migration(start_year, end_year,
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
                                             ]))

        QThreadPool.globalInstance().start(task)


        if hasattr(self, "eDNAButton"):
            self.eDNAButton.clicked.connect(self.on_eDNA_clicked)

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
        try:
            self.eDNA_results.setText("Loading...")

            self.elapsed_time = 0

            if hasattr(self, "loading_timer") and self.loading_timer.isActive():
                self.loading_timer.stop()

            self.loading_timer = QTimer(self)
            self.loading_timer.timeout.connect(self.update_loading_text)
            self.loading_timer.start(1000)


            def task_function():
                sampler = eDNASampler()
                results = sampler.generate_results()

                QTimer.singleShot(0, self.loading_timer.stop)

                # 'partial' to ensure UI update happens in main thread with the final results
                QTimer.singleShot(0, partial(self.eDNA_results.setText, '\n'.join(results)))

            task = GraphingTask(task_function)
            QThreadPool.globalInstance().start(task)

        except Exception as e:
            QMessageBox.warning(self, "Error", f"Error in eDNA sampling: {str(e)}")


    def update_loading_text(self):
        self.elapsed_time += 1
        self.eDNA_results.setText(f"Loading... ({self.elapsed_time}s)")


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
