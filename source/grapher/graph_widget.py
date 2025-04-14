import os
import time
from pathlib import Path

import numpy as np
import pandas as pd
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QMessageBox
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure


class GraphWidget(QWidget):
    def __init__(self, data_frame: pd.DataFrame, labels: [str], is_3d: bool, is_live: bool, title: str,
                 recording_update_signal=None,
                 recording_end_signal=None):
        super().__init__()
        self.data_frame = data_frame
        self.labels = labels
        self.is_3d = is_3d
        self.title = title
        self.is_live = is_live

        self.next_update = 0
        self.update_every = 1
        self.asked_overwrite = False

        layout = QVBoxLayout()
        self.setLayout(layout)

        self.canvas = None

        self.build_success = self.create_figure()

        if recording_update_signal is not None:
            recording_update_signal.connect(self.create_figure)

        if recording_end_signal is not None:
            recording_end_signal.connect(lambda: recording_update_signal.disconnect(self.create_figure))

    def create_figure(self) -> bool:
        if time.time() - self.next_update < self.update_every:
            return False
        self.next_update = time.time() + self.update_every

        print("Creaate figuree")
        # Create the figure
        figure = Figure(figsize=(8, 6))
        if self.is_3d:
            axis = figure.add_subplot(111, projection='3d')  # Ensure 3D plot
        else:
            axis = figure.add_subplot(111)

        axes = [np.array(self.data_frame[label].values) for label in self.labels]

        for i, label in enumerate(self.labels):
            if label == "Time":
                axes[i] -= axes[i][0]

        axis.plot(*axes)

        # Plot labels
        axis.set_title(self.title)
        axis.set_xlabel(self.labels[0])
        axis.set_ylabel(self.labels[1])
        if self.is_3d:
            axis.set_zlabel(self.labels[2])

        figure_save_dir = Path(os.getcwd()) / "Figures"

        if not figure_save_dir.exists():
            os.mkdir(figure_save_dir)

        figure_save_file = figure_save_dir / (self.title.replace(" ", "_") + ".png")

        if figure_save_file.exists() and not self.asked_overwrite:
            response = QMessageBox.warning(None, f"Figure Exists", f"A figure called {self.title} already exists. "
                                                                   f"Are you sure you want to overwrite it?",
                                           QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                                           QMessageBox.StandardButton.No
                                           )
            if response == QMessageBox.StandardButton.No:
                return False
            else:
                self.asked_overwrite = True

        figure.savefig(figure_save_file)

        self.update_canvas(figure)

        return True

    def update_canvas(self, figure) -> None:
        if self.canvas:
            self.layout().removeWidget(self.canvas)
            self.canvas.deleteLater()
            self.canvas = None

        # Creating new Matplotlib canvas and adding it to UI
        self.canvas = FigureCanvas(figure)
        self.layout().addWidget(self.canvas)
