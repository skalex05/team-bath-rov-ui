# This script creates a simulated version of the ROV that the UI can interact with
import pickle
from random import random, choice
from rov_data import ROVData
from stdout_type import StdoutType
from video_stream import VideoStream
from sock_stream_recv import SockStreamRecv
from sock_stream_send import SockStreamSend

# Temporary function to supply data to the UI
# Available Port Numbers: 49152-65535


rov_data = ROVData()


def get_rov_data():
    global rov_data

    rov_data.randomise()

    return rov_data


def rov_stdout_thread():
    rov_msgs = ["Swimming"]

    rov_errs = ["I'm sinking"]

    if random() < 0.9:
        payload = (StdoutType.ROV, choice(rov_msgs))
    else:
        payload = (StdoutType.ROV_ERROR, choice(rov_errs))

    return payload


def get_video_source(feed: VideoStream):
    if not feed.initialised:
        return None
    feed.update_camera_frame()
    return feed.camera_frame


def controller_input_recv(payload_bytes):
    global rov_data
    controller_input = pickle.loads(payload_bytes)

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




data_thread = SockStreamSend(None, "localhost", 52525, 0.05, get_rov_data, None)
data_thread.start()

stdout_thread = SockStreamSend(None, "localhost", 52535, 3, rov_stdout_thread, None)
stdout_thread.start()

video_streams = [VideoStream(i) for i in range(3)]

for i in range(3):
    video_thread = SockStreamSend(None, "localhost", 52524 - i, 0.0167,
                                  lambda j=i: get_video_source(video_streams[j]), None)
    video_thread.start()

input_thread = SockStreamRecv(None, "localhost", 52526, controller_input_recv, None)
input_thread.start()
