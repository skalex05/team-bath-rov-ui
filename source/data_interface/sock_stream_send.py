import pickle
import struct
import threading
from socket import socket, AF_INET, SOCK_STREAM
import time

# HEADER CONTENTS = (Message Size, Time Sent)
HEADER_FORMAT = "Qd"
HEADER_SIZE = struct.calcsize(HEADER_FORMAT)  # Header payload size is encoded as an unsigned long long


class SockStreamSend(threading.Thread):
    def __init__(self, app, addr, port, sleep, get_data, on_disconnect, *args, **kwargs):
        self.app = app  # This will be None if it is not running in the UI
        self.connected = False
        self.addr = addr
        self.port = port
        self.get_data = get_data
        self.on_disconnect = on_disconnect
        self.sleep = sleep
        super().__init__(*args, **kwargs)

    def run(self):
        while self.app is None or not self.app.closing:
            # Try and connect to server (Non-blocking)
            try:
                data_client = socket(AF_INET, SOCK_STREAM)
                data_client.settimeout(0.5)
                data_client.connect((self.addr, self.port))
            except TimeoutError:
                continue
            self.connected = True
            try:
                while self.app is None or not self.app.closing:
                    time.sleep(self.sleep)
                    # Get data from function
                    try:
                        data = self.get_data()
                        if data is None:
                            continue
                        bytes_to_send = pickle.dumps(data)
                    except Exception as e:
                        print(e)
                        continue

                    # Attach the header containing the size of payload
                    header = struct.pack("Qd", len(bytes_to_send), time.time())
                    payload = header+bytes_to_send
                    # Send all packets to the server
                    data_client.sendall(payload)
            # Allow program to reconnect if a connection/timeout error occurs
            except (ConnectionError, TimeoutError):
                self.connected = False
                if self.on_disconnect is not None:
                    self.on_disconnect()


