import time

from video_stream import VideoStream
from threading import Thread
import pickle
import struct
from socket import socket, SOCK_STREAM, AF_INET


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
                    time.sleep(0.0167)
            except ConnectionRefusedError:
                pass
            except ConnectionAbortedError:
                break


for i in range(2):
    thread = VideoSource(52524 - i, VideoStream(i))
    thread.start()
