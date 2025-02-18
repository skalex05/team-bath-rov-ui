import sys
import faulthandler
import io
from cProfile import Profile
from pstats import SortKey, Stats
from contextlib import redirect_stdout, redirect_stderr
from app import App

faulthandler.enable()

DEBUG = False  # STDOUT will not be displayed in the UI when set to True.

with Profile() as profile:
    # Catch standard output
    if DEBUG:
        app = App(sys.__stdout__, sys.__stderr__, sys.argv)
        exit_code = app.exec()
    else:
        stderr_io = io.StringIO()
        with redirect_stderr(stderr_io) as redirected_stderr:
            stdout_io = io.StringIO()
            with redirect_stdout(stdout_io) as redirected_stdout:
                app = App(redirected_stdout, redirected_stderr, sys.argv,)
                exit_code = app.exec()

    Stats(profile).strip_dirs().sort_stats(SortKey.TIME).print_stats()
    sys.exit(exit_code)
