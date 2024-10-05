import sys
import io
import screeninfo
from contextlib import redirect_stdout, redirect_stderr

from app import App
from pilot.pilot import Pilot
from copilot.copilot import Copilot
from grapher.grapher import Grapher
from nav_bar.nav_bar import NavBar
from dock import Dock

# Get all monitors connected to the computer
monitors = screeninfo.get_monitors()

app = App(sys.argv)

# Assign each window to its own monitor if available
pilot_monitor = 0
copilot_monitor = 0
graph_monitor = 0
if len(monitors) > 1:
    copilot_monitor = 1
    graph_monitor = 1
if len(monitors) > 2:
    graph_monitor = 2

# Build the dock container

dock = Dock(app, monitors[copilot_monitor], len(monitors))

# Create windows
pilot_window = Pilot(app, monitors[pilot_monitor])
copilot_window = Copilot(app, monitors[copilot_monitor])
grapher_window = Grapher(app, monitors[graph_monitor])

# Attach the navigation bars to these windows

pilot_window.attach_nav_bar(dock)
copilot_window.attach_nav_bar(dock)
grapher_window.attach_nav_bar(dock)

# Add windows to the dock
dock.addWidget(pilot_window)
dock.addWidget(copilot_window)
dock.addWidget(grapher_window)

# Undock windows if extra monitors are available
if len(monitors) > 1:
    pilot_window.nav.f_undock()

if len(monitors) > 2:
    grapher_window.nav.f_undock()

dock.showMaximized()

# Create the thread that will organise real time data

sio = io.StringIO()

# Catch standard output
with redirect_stderr(sio) as redirected_stderr:
    with redirect_stdout(sio) as redirected_stdout:
        app.init_data_interface([pilot_window, copilot_window, grapher_window],
                                redirected_stdout, redirected_stderr)

        sys.exit(app.exec())
