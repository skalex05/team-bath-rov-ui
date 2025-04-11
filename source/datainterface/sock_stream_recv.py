import struct
import sys
import threading
from socket import socket, AF_INET, SOCK_STREAM, IPPROTO_TCP, TCP_NODELAY, SOCK_DGRAM
import time
from typing import TYPE_CHECKING, Callable, Literal, Union

# HEADER CONTENTS = (Message Size, Time Sent, Send Sleep)
HEADER_FORMAT = "Qdf"
HEADER_SIZE = struct.calcsize(HEADER_FORMAT)

if TYPE_CHECKING:
    from app import App
    from rov_interface import ROVInterface


class SockStreamRecv(threading.Thread):
    def __init__(self, app: Union["App", "ROVInterface"], addr: str, port: int,
                 on_recv: Callable, on_connect: Callable = None, on_disconnect: Callable = None,
                 buffer_size: int = 1024, protocol: Literal["tcp", "udp"] = "tcp", timeout: float = 0.5):
        protocol = protocol.lower()
        if protocol not in ["tcp", "udp"]:
            raise ValueError("SockStream Protocol must either be TCP or UDP")
        self.connected = False
        self.addr = addr
        self.port = port
        self.on_recv = on_recv
        self.on_connect = on_connect
        self.on_disconnect = on_disconnect
        self.buffer_size = buffer_size
        self.protocol = protocol
        self.app = app
        self.timeout = timeout
        super().__init__()

    def run(self) -> None:
        # Run in either with either TCP or UDP protocols
        if self.protocol == "tcp":
            self.run_tcp()
        else:
            if self.buffer_size < 65535:
                print("Warning! SockStreamRecv with UDP protocol has a maximum buffer size of 65535 bytes",
                      file=sys.stderr)
                self.buffer_size = 65535
            self.run_udp()

    def run_udp(self) -> None:
        data_server = socket(AF_INET, SOCK_DGRAM)
        data_server.bind((self.addr, self.port))
        data_server.setblocking(False)
        last_msg = time.time()
        while not self.app.closing:
            time.sleep(0)  # Temporarily relinquish thread from CPU
            try:
                try:
                    payload, _ = data_server.recvfrom(self.buffer_size)
                    if not self.connected and self.on_connect:
                        self.on_connect()
                    self.connected = True
                except BlockingIOError:
                    if self.connected and time.time() - last_msg > self.timeout:
                        raise TimeoutError()
                    continue

                header, payload = payload[:HEADER_SIZE], payload[HEADER_SIZE:]
                try:
                    msg_size, recv_time, sleep = struct.unpack(HEADER_FORMAT, header)
                except struct.error:
                    print("Couldn't read header")
                    continue

                self.on_recv(payload)

                d = time.time() - last_msg
                if d < sleep:
                    time.sleep(sleep - d)
                    d = sleep
                last_msg = time.time()
                # if self.port == 52524:
                #     print(f"Receiving {len(payload)} bytes {1/(d+0.000000001)} times a second")
            except (ConnectionError, TimeoutError):
                # Socket was disconnected, reinitialise the socket to attempt to reconnect
                self.connected = False
                if self.on_disconnect:
                    self.on_disconnect()
                data_server = socket(AF_INET, SOCK_DGRAM)
                data_server.setblocking(False)
                data_server.bind((self.addr, self.port))
            except Exception as e:
                print(e)

    def run_tcp(self) -> None:
        data_server = socket(AF_INET, SOCK_STREAM)
        data_server.setsockopt(IPPROTO_TCP, TCP_NODELAY, 1)
        data_server.bind((self.addr, self.port))
        data_server.settimeout(self.timeout)

        while not self.app.closing:
            time.sleep(0)  # Temporarily relinquish thread from CPU
            try:
                data_server.listen()
                conn, _ = data_server.accept()
            except TimeoutError:  # Ensure non-blocking waiting for a connection
                continue
            if not self.connected and self.on_connect:
                self.on_connect()
            self.connected = True
            read_start = True
            payload = b""
            incoming_bytes = b""
            msg_size = 0
            try:
                while not self.app.closing:
                    time.sleep(0)
                    incoming_bytes += conn.recv(self.buffer_size)
                    # Connection has most likely failed if we are not receiving any bytes
                    # Only raise a connection error if we don't have any more messages to process
                    if len(incoming_bytes) < HEADER_SIZE and (msg_size == 0 or len(payload) < msg_size):
                        raise ConnectionError()

                    if read_start:  # If a message is beginning, find out how many bytes to expect
                        header, incoming_bytes = incoming_bytes[:HEADER_SIZE], incoming_bytes[HEADER_SIZE:]
                        try:
                            msg_size, recv_time, sleep = struct.unpack(HEADER_FORMAT, header)
                        except struct.error:
                            print("Couldn't read header:", header)

                        read_start = False

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

            # If the connection is broken, pass and wait to re-establish connection
            except (ConnectionError, TimeoutError):
                self.connected = False
                if self.on_disconnect:
                    self.on_disconnect()

    def is_connected(self) -> bool:
        return self.connected
