import sys
import io
from contextlib import redirect_stdout, redirect_stderr
import traceback
from app import App

# Create the thread that will organise real time data

sio = io.StringIO()

DEBUG = False  # STDOUT will not be displayed in the UI.

# Catch standard output
if DEBUG:
    app = App(sys.__stdout__, sys.__stderr__, sys.argv)
    sys.exit(app.exec())
else:
    with redirect_stderr(sio) as redirected_stderr:
        with redirect_stdout(sio) as redirected_stdout:
            app = App(redirected_stdout, redirected_stderr, sys.argv,)
            sys.exit(app.exec())
