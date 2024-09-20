import sys
import screeninfo

from PyQt6.QtWidgets import QApplication

from pilot.pilot import Pilot
from secondary_windows.copilot.copilot import Copilot
from secondary_windows.grapher.grapher import Grapher
from nav_bar.nav_widget import NavBar
from dock.dock import Dock

# Get all monitors connected to the computer
monitors = screeninfo.get_monitors()

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

dock = Dock(monitors[copilot_monitor])

pilot_window.nav = NavBar(pilot_window)
pilot_window.nav.show()

# Create secondary windows and add them to the dock
grapher_window = Grapher(monitors[graph_monitor])
copilot_window = Copilot(monitors[copilot_monitor])
dock.addWidget(grapher_window)
dock.addWidget(copilot_window)

# Attach the navigation bars to these windows

grapher_window.nav = NavBar(grapher_window, dock)
copilot_window.nav = NavBar(copilot_window, dock)
grapher_window.nav.generate_layout()
copilot_window.nav.generate_layout()
grapher_window.nav.show()
copilot_window.nav.show()

dock.showMaximized()

app.exec()
