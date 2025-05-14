import pickle
import struct
import threading
from socket import socket, AF_INET, SOCK_STREAM, SOCK_DGRAM, SOL_SOCKET, SO_REUSEADDR
import time
from typing import TYPE_CHECKING, Literal, Any, Union
from collections.abc import Callable
import sys

# HEADER CONTENTS = (Message Size, Time Sent, Send Sleep)
HEADER_FORMAT = "Qdf"

if TYPE_CHECKING:
    from app import App
    from rov_interface import ROVInterface


# Use to send a continuous stream of data
class SockStreamSend(threading.Thread):
    def __init__(self, app: Union["App", "ROVInterface"], addr: str, port: int, sleep: float,
                 get_data: Callable[[], bytes],
                 on_connect: Callable[[], None] = None, on_disconnect: Callable[[], None] = None,
                 protocol: Literal["tcp", "udp"] = "tcp", timeout: float = 0.5):
        protocol = protocol.lower()
        if protocol not in ["tcp", "udp"]:
            raise ValueError("SockStream Protocol must either be TCP or UDP")
        self.app = app
        self.connected = False
        self.addr = addr
        self.port = port
        self.get_data = get_data
        self.on_connect = on_connect
        self.on_disconnect = on_disconnect
        self.sleep = sleep
        self.protocol = protocol
        self.timeout = timeout
        super().__init__()

    def run(self) -> None:
        if self.protocol == "tcp":
            self.run_tcp()
        else:
            self.run_udp()

    def run_udp(self) -> None:
        data_client = socket(AF_INET, SOCK_DGRAM)
        data_client.setblocking(False)
        data_client.settimeout(self.timeout)
        data_client.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)

        print_conn_err = True
        while not self.app.closing:
            time.sleep(0)
            try:
                last_send = time.time()
                data = self.get_data()
                if data is None:
                    continue

                payload = struct.pack(HEADER_FORMAT, len(data), time.time(), self.sleep) + data

                data_client.sendto(payload, (self.addr, self.port))
                if not self.connected:
                    print_conn_err = True
                    self.connected = True
                    if self.on_connect:
                        self.on_connect()
                d = (time.time() - last_send)
                if d < self.sleep:
                    time.sleep(self.sleep - d)
            except (ConnectionError, TimeoutError, OSError) as e:
                if type(e) == OSError and print_conn_err:
                    print(f"Cannot connect on {self.addr}:{self.port}", file=sys.stderr)
                    print_conn_err = False

                if self.connected and self.on_disconnect is not None:
                    self.on_disconnect()
                self.connected = False
                data_client.close()
                data_client = socket(AF_INET, SOCK_DGRAM)
                data_client.setblocking(False)
                data_client.settimeout(self.timeout)
            except Exception as e:
                print(f"Unhandled Exception in TCP SockStreamSend thread {self.addr}:{self.port}", e, file=sys.stderr)
                continue
                
        data_client.close()
        print(f"Closed {self.addr}:{self.port}")

    def run_tcp(self) -> None:
        print_conn_err = True
        while not self.app.closing:
            time.sleep(0)  # Relinquish thread from CPU
            # Try and connect to server (Non-blocking)
            try:
                data_client = socket(AF_INET, SOCK_STREAM)
                data_client.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
                data_client.settimeout(self.timeout)
                data_client.connect((self.addr, self.port))
                if not self.connected and self.on_connect:
                    self.on_connect()
                self.connected = True
                print_conn_err = True
            except (TimeoutError, ConnectionError):
                continue
            except OSError:
                if print_conn_err:
                    print(f"Cannot connect on {self.addr}:{self.port}", file=sys.stderr)
                    print_conn_err = False
                continue
            except Exception as e:
                print(f"Exception in TCP SockStreamSend {self.addr}:{self.port}",e, file=sys.stderr)
                continue

            try:
                last_send = time.time()
                while not self.app.closing:
                    time.sleep(0)
                    d = (time.time() - last_send)
                    if d < self.sleep:
                        time.sleep(self.sleep - d)
                    last_send = time.time()
                    # Get data from function
                    try:
                        data = self.get_data()
                        if data is None:
                            continue
                    except Exception as e:
                        print(e, file=sys.stderr)
                        continue

                    # Attach the header containing the size of payload
                    header = struct.pack(HEADER_FORMAT, len(data), time.time(), self.sleep)
                    payload = header + data
                    # Send all packets to the server
                    data_client.sendall(payload)
            # Allow program to reconnect if a connection/timeout error occurs
            except Exception as e:
                print(f"Exception in TCP sock stream send thread {self.addr}:{self.port}", e, file=sys.stderr)
                self.connected = False
                if self.on_disconnect is not None:
                    self.on_disconnect()
            finally:
                data_client.close()
            print(f"Closed {self.addr}:{self.port}")

    def is_connected(self) -> bool:
        return self.connected


# Used to send a single message to a SockStreamRecv
# Note! This function is blocking! Do not use in main-threads!
# (Blocking won't be really noticed unless connection to socket fails)
def SockSend(app: Union["App", "ROVInterface"], addr: str, port: int, msg: Any, max_retries: int = 5) -> None:
    bytes_to_send = pickle.dumps(msg)
    # Attach the header containing the size of payload
    header = struct.pack(HEADER_FORMAT, len(bytes_to_send), time.time(), -1)
    payload = header + bytes_to_send
    retries = 0
    while not app.closing and (retries < max_retries):
        # Try and connect to server (Non-blocking)
        try:
            data_client = socket(AF_INET, SOCK_STREAM)
            data_client.settimeout(0.1)
            data_client.connect((addr, port))

            # Connected
            data_client.sendall(payload)

            break
        except (TimeoutError, ConnectionError):
            retries += 1
            pass
        except Exception as e:
            print(f"Unhandled Exception in sock stream send function {addr}:{port}", e, file=sys.stderr)
    if 1 <= max_retries <= retries:
        print(f"Couldn't send message: {msg} to {addr}:{port}")