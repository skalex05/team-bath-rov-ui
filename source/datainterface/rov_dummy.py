# This script creates a simulated version of the ROV that the UI can interact with
import pickle
import time
from random import random, choice
from threading import Thread

import cv2

from action_enum import ActionEnum
from rov_data import ROVData
from stdout_type import StdoutType
from video_stream import VideoStream
from sock_stream_recv import SockStreamRecv
from sock_stream_send import SockStreamSend, SockSend

# Temporary function to supply data to the UI
# Available Port Numbers: 49152-65535

rov_data = ROVData()

i = 100


def print_to_ui(msg, error=False):
    if error:
        payload = (StdoutType.ROV_ERROR, msg)
    else:
        payload = (StdoutType.ROV, msg)
    SockSend(None, "localhost", 52535, payload)


def get_rov_data():
    global rov_data
    global maintain_depth
    global i

    rov_data.randomise()
    rov_data.ambient_pressure = i
    i += 0.1
    i %= 50
    i += 100
    if maintain_depth:
        rov_data.depth = depth_value
    return pickle.dumps(rov_data)


def rov_stdout_thread():
    rov_msgs = ["Swimming"]

    rov_errs = ["I'm sinking"]

    while True:
        if random() < 0.9:
            print_to_ui(choice(rov_msgs))
        else:
            print_to_ui(choice(rov_errs), error=True)

        time.sleep(3)


def controller_input_recv(payload_bytes):
    global rov_data
    controller_input = pickle.loads(payload_bytes)
    if controller_input is None:
        return
    yaw_input = controller_input["axes"][0]
    roll_input = controller_input["hats"][0][0]
    pitch_input = controller_input["axes"][1]

    if abs(pitch_input) < 0.05:
        pitch_input = 0
    if abs(yaw_input) < 0.05:
        yaw_input = 0
    if abs(roll_input) < 0.05:
        roll_input = 0

    rov_data.attitude.y += yaw_input
    rov_data.attitude.x += pitch_input
    rov_data.attitude.z += roll_input


maintain_depth = False
depth_value = 0


def action_recv(payload_bytes):
    global rov_data
    global video_streams
    global maintain_depth
    global depth_value

    action = pickle.loads(payload_bytes)
    args = tuple()
    if type(action) is tuple:
        action, *args = action
    if action == ActionEnum.REINIT_CAMS:
        for stream in video_streams:
            stream.start_init_camera_feed()
        print_to_ui(f"Camera Feeds Re-initialised")
    if action == ActionEnum.MAINTAIN_ROV_DEPTH:
        maintain_depth = args[0]
        if maintain_depth:
            depth_value = args[1]
            print_to_ui(f"Maintaining Depth At {args[1]:.2f} m")
        else:
            print_to_ui("No Longer Maintaining Depth")


print_to_ui("Powering On...")

data_thread = SockStreamSend(None, "localhost", 52525, 0.05, get_rov_data, None)
data_thread.start()

video_streams = [VideoStream(i) for i in range(3)]

for i in range(3):
    video_thread = SockStreamSend(None, "localhost", 52524 - i, 0.033,
                                  video_streams[i].get_camera_frame, None, protocol="udp")
    video_thread.start()

stdout_thread = Thread(target=rov_stdout_thread)
stdout_thread.start()

input_thread = SockStreamRecv(None, "localhost", 52526, controller_input_recv,
                              lambda: print_to_ui("Controller Disconnected From ROV", True))
input_thread.start()

action_thread = SockStreamRecv(None, "localhost", 52527, action_recv)
action_thread.start()

print_to_ui("Powered On!")