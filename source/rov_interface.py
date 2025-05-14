# This script creates a simulated version of the ROV that the UI can interact with
import json
import os
import pickle
import sys
import time
from random import random, choice
from threading import Thread
import subprocess
import psutil
import serial

script_dir = os.path.dirname(os.path.abspath(__file__))  # Get the script's directory
os.chdir(script_dir)  # Change working directory to the script's location

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


thruster_matrix = [
        [0,     0,    -0.707,     0.707,     0.707,   -0.707],   # x
        [0,     0,     0.707,     0.707,     0.707,    0.707],   # y
        [1,     1,     0,         0,         0,        0],       # z
        [0,     0,    -0.0707,   -0.0707,    0.0707,  -0.0707],  # roll
        [-0.13, -0.13, -0.0707,   -0.0707,   -0.0707,  -0.0707], # yaw
        [0,     0,    -0.182,     0.182,    -0.182,    0.182]    # pitch
    ]

# Available Port Numbers: 49152-65535
class ROVInterface:
    def __init__(self, ui_ip=None, rov_ip=None, local_test=True, camera_count=3, use_new_camera_system=True, uart_port='/dev/ttyAMA0', uart_baud=115200):
        self.local_test = local_test
        self.use_new_camera_system = use_new_camera_system
        self.camera_count = camera_count
        self.uart_port = uart_port
        self.uart_baud = uart_baud
        self.uart = None

        # ROV state attributes

        self.closing = False
        self.hold_depth = 0
        self.maintain_depth = False

        
        if self.local_test:
            self.UI_IP = "localhost"
            self.ROV_IP = "localhost"
        else:
            self.UI_IP = ui_ip
            self.ROV_IP = rov_ip

        if self.UI_IP is None:
            raise ValueError(
                "Please set ui_ip parameter in rov_config.json of ROVInterface to the IP of the device you would like to connect to.")
        
        if self.ROV_IP is None:
            raise ValueError(
                "Please set rov_ip parameter in rov_config.json of ROVInterface to the IP of the ROV")
        
        print(
            f"Creating ROV Interface:\n{self.UI_IP=}\n{self.ROV_IP=}\n{self.use_new_camera_system=}\n{self.local_test=}\n{camera_count=}")

        self.rov_data = ROVData()
        self.i = 100  # temp variable

        self.print_to_ui("Powering On...")

        print(f"Binding Data Thread to {self.UI_IP} : {52525}")

        self.data_thread = SockStreamSend(self, self.UI_IP, 52525, 0.05, self.get_rov_data, None)
        self.data_thread.start()

        self.video_streams = None
        self.video_processes: [subprocess.Popen | None] = [None for _ in range(self.camera_count)]
        if not self.use_new_camera_system:
            self.video_streams = [VideoStream(i) for i in range(self.camera_count)]
        
        self.video_threads = []
        for i in range(self.camera_count):
            print("Binding video threads")
            if self.use_new_camera_system:
                print(f"\tBinding to {'127.0.0.1' if self.local_test else self.UI_IP} : {52524 - i}")
                video_thread = Thread(target=self.video_send,
                                      kwargs={"addr": "127.0.0.1" if self.local_test else self.UI_IP,
                                              "port": 52524 - i, "i": i})
            else:
                print(f"\tBinding to {'localhost' if self.local_test else self.UI_IP} : {52524 - i}")
                video_thread = SockStreamSend(self, "localhost" if self.local_test else self.UI_IP, 52524 - i, 0.0333,
                                              self.video_streams[i].get_camera_frame, None, protocol="udp")
            video_thread.start()
            
            self.video_threads.append(video_thread)

        self.stdout_thread = Thread(target=self.rov_stdout_thread)
        self.stdout_thread.start()

        if not self.use_new_camera_system:
            self.print_to_ui("ROV is using old camera system", error=True)

        print(f"Binding Input Thread to {self.ROV_IP} : {52526}")

        self.input_thread = SockStreamRecv(self, self.ROV_IP, 52526, self.controller_input_recv,
                                      lambda: self.print_to_ui("Controller Disconnected From ROV", True))
        self.input_thread.start()

        print(f"Binding Action Thread to {self.ROV_IP} : {52527}")

        self.action_thread = SockStreamRecv(self, self.ROV_IP, 52527, self.action_recv)
        self.action_thread.start()

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
        global thruster_matrix
        controller_data = pickle.loads(payload_bytes)
        if controller_data is None:
            return
        
        if self.uart is None or not self.uart.is_open:
            try:
                self.uart = serial.Serial(self.uart_port, self.uart_baud, timeout=1)
                print(f"✅ UART opened on {self.uart_port} at {self.uart_baud} baud.")
            except Exception as e:
                print(f"❌ Failed to open UART: {e}")
                return
            
            
        axes = controller_data.get('axes', [])
        hats = controller_data.get('hats', [])
        print("Received Controller Data:")
        print("Axes:   ", axes)
        print("Buttons:", controller_data.get('buttons', []))
        print("Hats:   ", hats)
        print("-" * 40)

        # Get up to 4 axes, pad with zeros if not enough
        x     = float(axes[0]) if len(axes) > 0 else 0.0
        z     = float(axes[1]) if len(axes) > 1 else 0.0
        roll  = float(axes[2]) if len(axes) > 2 else 0.0
        pitch = float(axes[3]) if len(axes) > 3 else 0.0

        # Clamp all axes to [-1, 1]
        x     = max(-1.0, min(1.0, x))
        z     = max(-1.0, min(1.0, z))
        roll  = max(-1.0, min(1.0, roll))
        pitch = max(-1.0, min(1.0, pitch))

        # Input vector for thruster mixing: [x, y, z, roll, yaw, pitch]
        # y and yaw are unused, so set to 0.0
        axes_in = [x, 0.0, z, roll, 0.0, pitch]

        # Matrix multiplication: thruster = T * axes_in
        thruster = []
        for i in range(6):
            value = sum(thruster_matrix[j][i] * axes_in[j] for j in range(6))
            thruster.append(value)

        # Format for ESP32: "val1,val2,val3,val4,val5,val6\n"
        data_str = ','.join(f"{v:.4f}" for v in thruster) + '\n'
        if self.uart.is_open:
            self.uart.write(data_str.encode())
            self.print_to_ui(f"Sent to ESP32: {data_str.strip()}")
        else:
            self.print_to_ui("Serial Connection to ESP32 Closed Unexpectedly")
        

    def action_recv(self, payload_bytes: bytes) -> None:
        print("Action Recieved")
        action = pickle.loads(payload_bytes)
        args = tuple()
        print(action)
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
            self.maintain_depth = args[0]
            
            if self.maintain_depth:
                self.print_to_ui(f"Maintaining Depth At {args[1]:.2f} m")
                self.hold_depth = args[1]
            else:
                self.print_to_ui("No Longer Maintaining Depth")
        elif action == ActionEnum.POWER_OFF_ROV:
            self.print_to_ui("Closing")
            self.close()
            
    def close(self):
        print("Closing ROV Interface")
        self.closing = True
        self.print_to_ui("Turning Off...")
        try:
            if self.action_thread.is_alive():
                self.action_thread.join(10)
        except Exception as e:
            print("Exception raised when closing Action Thread:", e, file=sys.stderr)
        print("Closed Action Thread")
        
        try:
            if self.input_thread.is_alive():
                self.input_thread.join(10)
        except Exception as e:
            print("Exception raised when closing Input Thread:", e, file=sys.stderr)
        print("Closed Input Thread")
        
        for video_thread in self.video_threads:
            try:
                if video_thread.is_alive():
                    video_thread.join(10)
            except Exception as e:
                print("Exception raised when closing Video Thread:", e, file=sys.stderr)
        print("Closed Video Threads")
        
        for i in range(self.camera_count):
            self.kill_video_process(i)
        print("Closed Video Processes")
            
        try:
            if self.data_thread.is_alive():
                self.data_thread.join(10)
        except Exception as e:
            print("Exception raised when closing Data Thread:", e, file=sys.stderr)
        print("Closed Data Thread")
        
        try:
            if self.stdout_thread.is_alive():
                self.stdout_thread.join(10)
        except Exception as e:
            print("Exception raised when closing STDOUT Thread:", e, file=sys.stderr)
        print("Closed STDOUT Thread")
        
        print("Closed")
    
    
    def video_send(self, addr: str, port: int, i: int) -> None:
        while not self.closing:
            self.kill_video_process(i)
            time.sleep(1)
            if self.local_test:
                if os.name == "nt":
                    process = (f'ffmpeg -fflags nobuffer -f dshow -i video="{camera_devices[i]}" '
                               '-b:v 16M -preset ultrafast -tune zerolatency -g 30 '
                               f' -r 30 -s 1920x1080 -preset fast -f mpegts udp://{addr}:{port}')

                elif os.name == "posix":
                    process = (f'ffmpeg -f avfoundation -i "{i}" -c:v libx264 '
                               '-b:v 4M -preset ultrafast -tune zerolatency -g 30 '
                               f'-preset ultrafast -f mpegts udp://{addr}:{port}')
                else:
                    print("Warning: Detected you are not running on Windows or Mac.\n"
                          "If you are running this on the Raspberry PI, please set local_test to False",
                          file=sys.stderr)
                    process = (f"rpicam-vid -t {i} -n --width 1920 --height 1080"
                               f" --codec libav --libav-format mpegts"
                               f" --bitrate 30000000"
                               f" -o udp://{addr}:{port}")
            else:
                process = (f"rpicam-vid -t {i} -n --width 2028 --height 1080"
                           # f" --codec libav --libav-format mpegts"
                           f" --codec h264"
                           f" --bitrate 6000000"
                           # f" --profile high --level 4.2"
                           f" --intra 1"
                           f" --framerate 20"
                           " --low-latency"
                           f" -o udp://{addr}:{port}")
            process = subprocess.Popen(process, shell=True)
            self.video_processes[i] = process
            time.sleep(1)
            while process.poll() is None and not self.closing:
                pass

try:
    with open("rov_config.json", "r") as f:
        config_file = json.load(f)
    print(config_file)
    interface = ROVInterface(**config_file)
    
    while not interface.closing:
        time.sleep(0)
        
except FileNotFoundError:
    print(("Please create rov_config.json to the specification in ROV_INTERFACE_INSTALL.md.\nThis file should look like:\n" 
            "{\n"
            '\t"ui_ip": <YOUR LAPTOP\'s IP>",\n'
            '\t"local_test": false,\n'
            '\t"camera_count": 3\n'
            '}'),
            file=sys.stderr)
except json.decoder.JSONDecodeError:
    print("Malformed rov_config.json file", file=sys.stderr)