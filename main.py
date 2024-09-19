import sys
import screeninfo

from PyQt6.QtWidgets import QApplication, QTabWidget

from pilot.pilot import Pilot
from secondary_windows.copilot.copilot import Copilot
from secondary_windows.grapher.grapher import Grapher

# Get all monitors connected to the computer
monitors = screeninfo.get_monitors()
for monitor in monitors:
    print(monitor)

app = QApplication(sys.argv)

# Assign each window to its own monitor if available
pilot_monitor = 0
copilot_monitor = 0
graph_monitor = 0
if len(monitors) > 1:
    copilot_monitor = 1
    graph_monitor = 1
if len(monitors) > 2:
    graph_monitor = 2

pilot_window = Pilot(monitors[pilot_monitor])

# Build the docked window
# This will by default store the copilot and grapher windows
# These windows can be floated and re-docked when needed

# Copilot is the primary docked window
dock_monitor = monitors[copilot_monitor]
dock = QTabWidget()
dock.setGeometry(dock_monitor.x, dock_monitor.y, dock_monitor.width, dock_monitor.height)

grapher_window = Grapher(monitors[graph_monitor])
copilot_window = Copilot(monitors[copilot_monitor])

def on_tab_change(tab_i):
    dock.setWindowTitle(dock.currentWidget().windowTitle())


dock.currentChanged.connect(on_tab_change)

dock.addTab(grapher_window, grapher_window.windowTitle())
dock.addTab(copilot_window, copilot_window.windowTitle())

dock.showMaximized()

app.exec()
