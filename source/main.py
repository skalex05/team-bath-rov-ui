import sys
import io
from contextlib import redirect_stdout, redirect_stderr
from app import App
import os

if os.name == "nt":
    import ctypes
    scale = 100 / ctypes.windll.shcore.GetScaleFactorForDevice(0)
    os.environ["QT_SCALE_FACTOR"] = str(scale)
else:
    print("WARNING: Display Scaling May Not Be Correct on non ")
    os.environ["QT_USE_PHYSICAL_DPI"] = "1"

# Create the thread that will organise real time data

DEBUG = False  # STDOUT will not be displayed in the UI when set to True.

# Catch standard output
if DEBUG:
    app = App(sys.__stdout__, sys.__stderr__, sys.argv)
    sys.exit(app.exec())
else:
    stderr_io = io.StringIO()
    with redirect_stderr(stderr_io) as redirected_stderr:
        stdout_io = io.StringIO()
        with redirect_stdout(stdout_io) as redirected_stdout:
            app = App(redirected_stdout, redirected_stderr, sys.argv,)
            sys.exit(app.exec())
