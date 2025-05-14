import sys
import faulthandler
import io
from cProfile import Profile
from pstats import SortKey, Stats
from contextlib import redirect_stdout, redirect_stderr
from app import App

faulthandler.enable()

DEBUG = False  # STDOUT will not be displayed in the UI when set to True.
RUN_ROV_LOCALLY = False  # Set this to true to create dummy processes for the ROV
USE_NEW_CAMERA_SYSTEM = True
ROV_IP = "192.168.1.133"
FLOAT_IP = "localhost"

with Profile() as profile:
    # Catch standard output
    if DEBUG:
        app = App(sys.__stdout__, sys.__stderr__, sys.argv, RUN_ROV_LOCALLY, USE_NEW_CAMERA_SYSTEM, ROV_IP, FLOAT_IP)
        exit_code = app.exec()
    else:
        stderr_io = io.StringIO()
        with redirect_stderr(stderr_io) as redirected_stderr:
            stdout_io = io.StringIO()
            with redirect_stdout(stdout_io) as redirected_stdout:
                app = App(redirected_stdout, redirected_stderr, sys.argv, RUN_ROV_LOCALLY, USE_NEW_CAMERA_SYSTEM, ROV_IP, FLOAT_IP)
                exit_code = app.exec()

    Stats(profile).strip_dirs().sort_stats(SortKey.TIME).print_stats()
    sys.exit(exit_code)
