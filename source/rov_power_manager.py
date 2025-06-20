import json
import time
import sys
import pickle
import subprocess
import os

script_dir = os.path.dirname(os.path.abspath(__file__))  # Get the script's directory
os.chdir(script_dir)  # Change working directory to the script's location

from datainterface.sock_stream_recv import SockStreamRecv
from data_classes.action_enum import ActionEnum

script = "python3 rov_interface.py"


class Closeable:
    def __init__(self):
        self.closing = False


def on_signal_recv(payload_bytes):
    pickle.loads(payload_bytes)

    action = pickle.loads(payload_bytes)
    args = tuple()
    if type(action) is tuple:
        action, *args = action

    if action == ActionEnum.POWER_ON_ROV:
        print("Power On Signal Received")
        subprocess.Popen(script, shell=True)


try:
    with open("rov_config.json", "r") as f:
        config_file = json.load(f)

    closeable = Closeable()

    receiver = SockStreamRecv(closeable, config_file["rov_ip"], config_file["port_bindings"]["power"], on_signal_recv)
    receiver.start()
    print("Waiting")
    subprocess.Popen(script, shell=True)
    try:
        while 1:
            time.sleep(0)
    except KeyboardInterrupt:
        print("Closing")
        closeable.closing = True
        receiver.join(10)
        time.sleep(5)
        print("Closed Successfully")


except FileNotFoundError:
    print((
              "Please create rov_config.json to the specification in ROV_INTERFACE_INSTALL.md.\nThis file should look like:\n"
              "{\n"
              '\t"ui_ip": <YOUR LAPTOP\'s IP>",\n'
              '\t"local_test": false,\n'
              '\t"camera_count": 3\n'
              '}'),
          file=sys.stderr)
except json.decoder.JSONDecodeError:
    print("Malformed rov_config.json file", file=sys.stderr)
