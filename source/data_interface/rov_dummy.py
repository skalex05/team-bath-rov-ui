# This script creates a simulated version of the ROV that the UI can interact with
import time
import struct
import pickle
from random import random, choice
from socket import socket, SOCK_DGRAM, SOCK_STREAM, AF_INET
from rov_data import ROVData
from stdout_type import StdoutType
from video_stream import VideoStream
from threading import Thread


# Temporary function to supply data to the UI
# Available Port Numbers: 49152-65535

def rov_data_thread():
    data_client = socket(AF_INET, SOCK_DGRAM)

    rov_data = ROVData()

    i = 0
    while 1:
        try:
            rov_data.randomise()
            payload = pickle.dumps(rov_data)
            data_client.sendto(payload, ("localhost", 52525))
            i += 1
        except ConnectionError:
            print("ERR")


def rov_stdout_thread():
    data_client = socket(AF_INET, SOCK_STREAM)
    data_client.connect(("localhost", 52535))

    rov_msgs = ["Swimming"]

    rov_errs = ["I'm sinking"]

    i = 0
    while 1:
        try:
            if random() < 0.9:
                payload = pickle.dumps((StdoutType.ROV, choice(rov_msgs)))
            else:
                payload = pickle.dumps((StdoutType.ROV_ERROR, choice(rov_errs)))
            data_client.send(payload)
            i += 1
        except ConnectionError as e:
            print("ERR", e)
        time.sleep(random() * 5)


class VideoSource(Thread):
    def __init__(self, port, feed: VideoStream):
        self.feed: VideoStream = feed
        self.port = port
        super().__init__()

    def run(self):
        while 1:
            try:
                client_socket = socket(AF_INET, SOCK_STREAM)
                while not self.feed.initialised:
                    pass
                self.feed.update_camera_frame()
                frame_bytes = pickle.dumps(self.feed.camera_frame)
                client_socket.connect(("localhost", self.port))
                pack = struct.pack("Q", len(frame_bytes))
                client_socket.send(pack)
                handshake = client_socket.recv(8)
                handshake = struct.unpack("Q", handshake)[0]
                if handshake != len(frame_bytes):
                    raise Exception("Handshake failed")
                while True:
                    self.feed.update_camera_frame()
                    frame_bytes = pickle.dumps(self.feed.camera_frame)
                    client_socket.sendall(frame_bytes)
            except ConnectionRefusedError:
                pass
            except ConnectionAbortedError:
                break


def video_source_thread():
    for i in range(2):
        thread = VideoSource(52524 - i, VideoStream(i))
        thread.start()


def controller_input_receiver_thread():
    stdout_server = socket(AF_INET, SOCK_STREAM)
    stdout_server.bind(("localhost", 52526))
    stdout_server.settimeout(0.5)

    conn, _ = None, None
    while 1:
        try:
            try:
                if conn is None:
                    raise ConnectionError()
                controller_input, send_time = pickle.loads(conn.recv(1024))
                print(controller_input)
            except ConnectionError:
                stdout_server.listen()
                conn, _ = stdout_server.accept()
        except TimeoutError:
            pass
        except Exception as e:
            print(e)
        time.sleep(0.01)


data_thread = Thread(target=rov_data_thread)
data_thread.start()

stdout_thread = Thread(target=rov_stdout_thread)
stdout_thread.start()

video_thread = Thread(target=video_source_thread)
video_thread.start()

input_thread = Thread(target=controller_input_receiver_thread)
input_thread.start()