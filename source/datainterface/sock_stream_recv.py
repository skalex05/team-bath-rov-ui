import struct
import threading
from socket import socket, AF_INET, SOCK_STREAM
import time

# HEADER CONTENTS = (Message Size, Time Sent)
HEADER_FORMAT = "Qd"
HEADER_SIZE = struct.calcsize(HEADER_FORMAT)  # Header payload size is encoded as an unsigned long long


class SockStreamRecv(threading.Thread):
    def __init__(self, app, addr, port, on_recv, on_disconnect, *args, **kwargs):
        self.connected = False
        self.addr = addr
        self.port = port
        self.on_recv = on_recv
        self.on_disconnect = on_disconnect
        self.app = app
        super().__init__(*args, **kwargs)

    def run(self):
        data_server = socket(AF_INET, SOCK_STREAM)
        data_server.bind((self.addr, self.port))
        data_server.settimeout(0.5)

        while self.app is None or not self.app.closing:
            try:
                data_server.listen()
                conn, _ = data_server.accept()
            except TimeoutError:  # Ensure non-blocking waiting for a connection
                continue
            self.connected = True
            read_start = True
            payload = b""
            incoming_bytes = b""
            msg_size = 0
            try:
                while self.app is None or not self.app.closing:
                    incoming_bytes += conn.recv(1048576)

                    # Connection has most likely failed if we are not receiving any bytes
                    # Only raise a connection error if we don't have any more messages to process
                    if len(incoming_bytes) < HEADER_SIZE and (len(payload) < msg_size or msg_size == 0):
                        raise ConnectionError()

                    if read_start:  # If a message is beginning, find out how many bytes to expect
                        header, incoming_bytes = incoming_bytes[:HEADER_SIZE], incoming_bytes[HEADER_SIZE:]
                        try:
                            msg_size, recv_time = struct.unpack(HEADER_FORMAT, header)
                        except struct.error:
                            print(header)

                        read_start = False
                        # if self.port == 52526 or self.port == 52525 or self.port == 52524:
                        #     print(self.port, time.time() - recv_time)

                    payload += incoming_bytes

                    if len(payload) >= msg_size:  # Message Received
                        payload, incoming_bytes = payload[:msg_size], payload[msg_size:]

                        # Allow the next message to be received.
                        read_start = True

                        # Process the payload bytes
                        self.on_recv(payload)

                        payload = b""
                    else:
                        incoming_bytes = b""

            # If the connection is broken, pass and wait to reestablish connection
            except (ConnectionError, TimeoutError):
                self.connected = False
                if self.on_disconnect is not None:
                    self.on_disconnect()
