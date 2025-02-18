import os
import numpy as np
import traceback
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

class GraphGenerator:
    '''
    Responsible for:
        - Reading data from 'live_data.txt'
        - Generating graphs
        - Embedding graphs in UI

    Currently this is reading from a txt file. The serialSimulator.py file can be run to simulate live data from
    serial com or something. Or just run it and stop it to copy data from the csv into the text file.
    '''
    def __init__(self):
        self.canvas = None # Placeholder for Matplotlib canvas

    def read_data(self, file_name="live_data.txt"):
        """Reads data from live_data.txt inside the grapher folder."""
        project_root = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))  # Moves up one level, it was buggy before

        # Construct the correct path to the 'grapher' folder
        file_path = os.path.join(project_root, "grapher", file_name)

        print(f"Reading data from {file_path}...")

        try:
            # Read CSV file
            data = np.loadtxt(file_path, delimiter=",", skiprows=1)
            packet_number = data[:, 0]
            accel_x = data[:, 4]
            accel_y = data[:, 5]
            accel_z = data[:, 6]
            print("Data successfully read!")
            return packet_number, accel_x, accel_y, accel_z
        except Exception as e:
            print(f"Error reading file: {e}")
            return None, None, None, None

    def generate_acceleration(self, graph_area, packet_number, x=None, y=None, z=None, save_path="acceleration.png"):
        """Generates an acceleration graph for selected components and embeds it in the graph area."""
        try:
            print(f"Graphing Data: Packet Numbers={packet_number[:10] if packet_number is not None else 'None'}")
            print(f"X={x[:10] if x is not None else 'None'}, Y={y[:10] if y is not None else 'None'}, Z={z[:10] if z is not None else 'None'}")

            # Ensure data is valid
            if packet_number is None or (x is None and y is None and z is None):
                print("Error: No valid data to plot!")
                return

            # Ensure at least one acceleration array is not empty
            if all(arr is not None and len(arr) == 0 for arr in [x, y, z]):
                print("Error: All acceleration arrays are empty!")
                return

            print("Generating acceleration graph...")

            # Ensure all arrays are the same length
            min_length = min(len(packet_number), len(x) if x is not None else float('inf'),
                             len(y) if y is not None else float('inf'),
                             len(z) if z is not None else float('inf'))

            packet_number = packet_number[:min_length]
            x = x[:min_length] if x is not None else None
            y = y[:min_length] if y is not None else None
            z = z[:min_length] if z is not None else None

            print(f"Using trimmed arrays of size {min_length}")

            # Create figure
            figure = Figure(figsize=(8, 6))
            axis = figure.add_subplot(111)
            time = packet_number * 0.01  # Convert packet numbers to time ~~~~~~~~~~HERE TO ADJUST TIME~~~~~~~~~~~~~~

            # Plot the selected acceleration components
            if x is not None:
                axis.plot(time, x, label='Acceleration X', linewidth=1.5)
            if y is not None:
                axis.plot(time, y, label='Acceleration Y', linewidth=1.5)
            if z is not None:
                axis.plot(time, z, label='Acceleration Z', linewidth=1.5)

            # Plot labels
            axis.set_title('Acceleration vs Time', fontsize=14)
            axis.set_xlabel('Time (seconds)', fontsize=12)
            axis.set_ylabel('Acceleration (m/s²)', fontsize=12)
            axis.legend()
            axis.grid(True)

            # Saving figure as images to use as button icons
            print("Saving acceleration graph...")
            figure.savefig(save_path)
            print(f"Graph saved as {save_path}")

            # Update UI with graph
            self._update_canvas(graph_area, figure)
            print("Graph displayed successfully!")

        except Exception as e:
            print(f"Unhandled Error: {str(e)}")
            traceback.print_exc()


    def generate_depth_plot(self, graph_area, packet_number, accel_x, accel_y, accel_z, dt=0.01, save_path='depth.png'):
        """Generates a 3D depth plot and embeds it in the graph area."""
        try:
            if packet_number is None or accel_x is None or accel_y is None or accel_z is None:
                print("No data to plot.")
                return

            print("Generating depth plot...")

            # Integrate acceleration to get velocity   ~~~~~VELOCITY data can be taken from here~~~~
            velocity_x = np.cumsum(accel_x) * dt
            velocity_y = np.cumsum(accel_y) * dt
            velocity_z = np.cumsum(accel_z) * dt

            # Integrate velocity to get position
            position_x = np.cumsum(velocity_x) * dt
            position_y = np.cumsum(velocity_y) * dt
            position_z = np.cumsum(velocity_z) * dt

            # Create the figure
            figure = Figure(figsize=(8, 6))
            axis = figure.add_subplot(111, projection='3d')  # Ensure 3D plot
            axis.plot(position_x, position_y, position_z, label='Position', color='blue')

            # Plot labels
            axis.set_title('3D Positional Data from IMU')
            axis.set_xlabel('Position X (m)')
            axis.set_ylabel('Position Y (m)')
            axis.set_zlabel('Position Z (m)')
            axis.legend()

            # Save the figure as an image
            figure.savefig(save_path)
            print(f"Depth plot saved as {save_path}")

            #update UI with graph
            self._update_canvas(graph_area, figure)
            print("Depth plot displayed!")

        except Exception as e:
            print(f"Unhandled Error in generate_depth_plot: {str(e)}")
            import traceback
            traceback.print_exc()

    def _update_canvas(self, graph_area, figure):
        """Clears previous graph and embeds a new one in the graph area."""
        if self.canvas:
            graph_area.layout().removeWidget(self.canvas)
            self.canvas.deleteLater()
            self.canvas = None
            print("Previous canvas removed.")

        # Creating new Matplotlib canvas and adding it to UI
        self.canvas = FigureCanvas(figure)
        graph_area.layout().addWidget(self.canvas)
        print("Canvas updated!")
