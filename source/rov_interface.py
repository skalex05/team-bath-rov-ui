# This script creates a simulated version of the ROV that the UI can interact with
import os
import pickle
import sys
import time
from random import random, choice
from threading import Thread
import subprocess
import psutil

from data_classes.action_enum import ActionEnum
from rov_float_data_structures.rov_data import ROVData
from data_classes.stdout_type import StdoutType
from datainterface.video_stream import VideoStream
from datainterface.sock_stream_recv import SockStreamRecv
from datainterface.sock_stream_send import SockStreamSend, SockSend

if os.name == "nt":
    from pygrabber.dshow_graph import FilterGraph

    graph = FilterGraph()
    camera_devices = graph.get_input_devices()


# Available Port Numbers: 49152-65535
class ROVInterface:
    def __init__(self, ui_ip=None, local_test=True, camera_count=3, use_new_camera_system=True):
        self.local_test = local_test
        self.use_new_camera_system = use_new_camera_system
        self.camera_count = camera_count

        self.ROV_IP = "0.0.0.0"
        if self.local_test:
            self.UI_IP = "localhost"
        else:
            self.UI_IP = ui_ip

        if self.UI_IP is None:
            raise "Please set ui_ip parameter of ROVInterface to the IP of the device you would like to connect to."

        self.rov_data = ROVData()
        self.i = 100  # temp variable

        # ROV state attributes

        self.closing = False
        self.hold_depth = 0
        self.maintain_depth = False

        self.print_to_ui("Powering On...")

        data_thread = SockStreamSend(self, self.UI_IP, 52525, 0.05, self.get_rov_data, None)
        data_thread.start()

        self.video_streams = None
        self.video_processes: [subprocess.Popen | None] = [None for _ in range(self.camera_count)]
        if not self.use_new_camera_system:
            self.video_streams = [VideoStream(i) for i in range(self.camera_count)]

        for i in range(self.camera_count):
            if self.use_new_camera_system:
                video_thread = Thread(target=self.video_send,
                                      kwargs={"addr": "127.0.0.1" if self.local_test else self.ROV_IP,
                                              "port": 52524 - i, "i": i})
            else:
                video_thread = SockStreamSend(self, "localhost" if self.local_test else self.UI_IP, 52524 - i, 0.0333,
                                              self.video_streams[i].get_camera_frame, None, protocol="udp")
            video_thread.start()

        stdout_thread = Thread(target=self.rov_stdout_thread)
        stdout_thread.start()

        if not self.use_new_camera_system:
            self.print_to_ui("ROV is using old camera system", error=True)

        input_thread = SockStreamRecv(self, self.ROV_IP, 52526, self.controller_input_recv,
                                      lambda: self.print_to_ui("Controller Disconnected From ROV", True))
        input_thread.start()

        action_thread = SockStreamRecv(self, self.ROV_IP, 52527, self.action_recv)
        action_thread.start()

        self.print_to_ui("Powered On!")

    def print_to_ui(self, msg, error=False) -> None:
        if error:
            payload = (StdoutType.ROV_ERROR, msg)
        else:
            payload = (StdoutType.ROV, msg)
        SockSend(self, self.UI_IP, 52535, payload)

    def get_rov_data(self) -> bytes:
        self.rov_data.randomise()
        self.rov_data.ambient_pressure = self.i
        self.i += 0.1
        self.i %= 50
        self.i += 100

        if self.rov_data.attitude.x < -180:
            self.rov_data.attitude.x = 360 + self.rov_data.attitude.x
        if self.rov_data.attitude.x > 180:
            self.rov_data.attitude.x = -(360 + self.rov_data.attitude.x)

        if self.rov_data.attitude.y < -180:
            self.rov_data.attitude.y = 360 + self.rov_data.attitude.y
        if self.rov_data.attitude.y > 180:
            self.rov_data.attitude.y = -(360 + self.rov_data.attitude.y)

        if self.rov_data.attitude.z < -180:
            self.rov_data.attitude.z = 360 + self.rov_data.attitude.z
        if self.rov_data.attitude.z > 180:
            self.rov_data.attitude.z = -(360 + self.rov_data.attitude.z)

        self.rov_data.depth += 0.01
        self.rov_data.depth %= 5

        if self.maintain_depth:
            self.rov_data.depth = self.hold_depth
        return pickle.dumps(self.rov_data)

    def kill_video_process(self, i):
        process = self.video_processes[i]
        if process is not None:
            try:
                process = psutil.Process(process.pid)
                for child in process.children(recursive=True):
                    child.terminate()
                process.terminate()
            except psutil.NoSuchProcess:
                pass

        self.video_processes[i] = None

    def rov_stdout_thread(self) -> None:
        rov_msgs = ["Swimming"]

        rov_errs = ["I'm sinking"]

        while not self.closing:
            if random() < 0.9:
                self.print_to_ui(choice(rov_msgs))
            else:
                self.print_to_ui(choice(rov_errs), error=True)

            time.sleep(3)

    def controller_input_recv(self, payload_bytes: bytes) -> None:
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

        self.rov_data.attitude.y += yaw_input
        self.rov_data.attitude.x += pitch_input
        self.rov_data.attitude.z += roll_input

    def action_recv(self, payload_bytes: bytes) -> None:
        action = pickle.loads(payload_bytes)
        args = tuple()
        if type(action) is tuple:
            action, *args = action
        if action == ActionEnum.REINIT_CAMS:
            if self.use_new_camera_system:
                for i in range(self.camera_count):
                    self.kill_video_process(i)
            else:
                for stream in self.video_streams:
                    stream.start_init_camera_feed()
            self.print_to_ui(f"Camera Feeds Re-initialised")
        elif action == ActionEnum.MAINTAIN_ROV_DEPTH:
            maintain_depth = args[0]
            if maintain_depth:
                self.print_to_ui(f"Maintaining Depth At {args[1]:.2f} m")
            else:
                self.print_to_ui("No Longer Maintaining Depth")
        elif action == ActionEnum.POWER_OFF_ROV:
            self.print_to_ui("Turning Off...")
            self.closing = True
            for i in range(self.camera_count):
                self.kill_video_process(i)
            exit()

    def video_send(self, addr: str, port: int, i: int) -> None:
        while not self.closing:
            self.kill_video_process(i)
            time.sleep(1)
            if self.local_test:
                if os.name == "nt":
                    process = subprocess.Popen(
                        f'ffmpeg -fflags nobuffer -f dshow -i video="{camera_devices[i]}" '
                        '-b:v 16M -preset ultrafast -tune zerolatency -g 30 '
                        f' -r 30 -s 1920x1080 -preset fast -f mpegts udp://{addr}:{port}', shell=True)
                    print(f'ffmpeg -fflags nobuffer -f dshow -i video="{camera_devices[i]}" '
                          '-b:v 4M -preset ultrafast -tune zerolatency -g 30 '
                          f' -r 30 -s 1920x1080 -preset fast -f mpegts udp://{addr}:{port}')
                elif os.name == "posix":
                    process = subprocess.Popen(f'ffmpeg -f avfoundation -i "{i}" -c:v libx264 '
                                               '-b:v 4M -preset ultrafast -tune zerolatency -g 30 '
                                               f'-preset ultrafast -f mpegts udp://{addr}:{port}')
                else:
                    print("Warning: Detected you are not running on Windows or Mac.\n"
                          "If you are running this on the Raspberry PI, please set local_test to False",
                          file=sys.stderr)
                    process = subprocess.Popen(f'ffmpeg -f avfoundation -i "{i}" -c:v libx264 '
                                               f'-preset ultrafast -f mpegts udp://{addr}:{port}')
            else:

                process = subprocess.Popen(f"rpicam-vid -t {i} -n --codec libav --libav-format mpegts "
                                           f"--low-latency -o udp://{addr}:{port}", shell=True)
            self.video_processes[i] = process
            time.sleep(1)
            while process.poll() is None and not self.closing:
                pass


ROVInterface(camera_count=3)

