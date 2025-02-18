import os
import sys
import traceback

from PyQt6.QtWidgets import QApplication, QVBoxLayout, QLabel, QMessageBox
from PyQt6.QtGui import QIcon

from matplotlib.backends.backend_qtagg import NavigationToolbar2QT as NavigationToolbar
from grapher.graphGenerator import GraphGenerator
from grapher.eDNASampler import eDNASampler
from window import Window

path_dir = os.path.dirname(os.path.realpath(__file__))

class Grapher(Window):
    def __init__(self, *args):
        super().__init__(os.path.join(path_dir, "grapher.ui"), *args)

        self.graph_generator = GraphGenerator() # From graphGenerator.py
        self.toolbar = None

        self.eDNA_results: QLabel = self.findChild(QLabel, "eDNA_results")

        if self.graphArea.layout() is None: # Making sure graph area has layout
            self.graphArea.setLayout(QVBoxLayout())


        # Enable checkboxes for vel & acceleration axes
        for attr in ["velocityX", "velocityY", "velocityZ", "accelerationX", "accelerationY", "accelerationZ"]:
            checkbox = getattr(self, attr, None)
            if checkbox:
                checkbox.setChecked(True)

        #Connecting buttons
        if hasattr(self, "velocityDropdownButton"):
            self.velocityDropdownButton.clicked.connect(self.on_velocity_dropdown_clicked)
        if hasattr(self, "accelerationDropdownButton"):
            self.accelerationDropdownButton.clicked.connect(self.on_acceleration_dropdown_clicked)

        if hasattr(self, "velocityButton"):
            self.velocityButton.clicked.connect(self.on_velocity_clicked)
        if hasattr(self, "accelerationButton"):
            self.accelerationButton.clicked.connect(self.on_acceleration_clicked)
        if hasattr(self, "depthButton"):
            self.depthButton.clicked.connect(self.on_depth_clicked)

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
        """Generate velocity plot.""" # for now showing acceleration as placeholder, just integrate data in graphGen for v
        packet_number, accel_x, accel_y, accel_z = self.graph_generator.read_data()

        # Checking which velocity axes are to be used
        x = accel_x if getattr(self, "velocityX", None) and self.velocityX.isChecked() else None
        y = accel_y if getattr(self, "velocityY", None) and self.velocityY.isChecked() else None
        z = accel_z if getattr(self, "velocityZ", None) and self.velocityZ.isChecked() else None


        if x is None and y is None and z is None:
            print("Error: No velocity components selected!")
            return

        print(f"Selected Data for Plotting: X={x}, Y={y}, Z={z}")

        #Generating graph
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

        #graphing
        self.graph_generator.generate_acceleration(self.graphArea, packet_number, x, y, z, save_path="acceleration.png")
        self.update_button_icon("accelerationButton", "acceleration.png")
        self.add_toolbar(self.graph_generator.canvas)

    def on_depth_clicked(self):
        """Generate depth plot."""
        try: # It kept crashing, so I added this. It's working now
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
            self.graph_generator.generate_depth_plot(self.graphArea, packet_number, accel_x, accel_y, accel_z, save_path="depth.png")

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
            sampler = eDNASampler()
            results = sampler.generate_results()
            self.eDNA_results.setText('\n'.join(results))
        except:
            QMessageBox.warning("Error in eDNA sampling. Check pytesseract and image locations")

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
