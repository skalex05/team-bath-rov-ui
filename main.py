import sys
import io
from contextlib import redirect_stdout, redirect_stderr

from app import App

app = App(sys.argv)

# Create the thread that will organise real time data

sio = io.StringIO()

# Catch standard output
with redirect_stderr(sio) as redirected_stderr:
    with redirect_stdout(sio) as redirected_stdout:
        app.init_data_interface(redirected_stdout, redirected_stderr)

        sys.exit(app.exec())
