import struct
import sys
import threading
import logging
from socket import socket, AF_INET, SOCK_STREAM, IPPROTO_TCP, TCP_NODELAY, SOCK_DGRAM, gaierror, SOL_SOCKET, \
    SO_REUSEADDR
import time
from typing import TYPE_CHECKING, Callable, Literal, Union, Optional
from dataclasses import dataclass
from enum import Enum

# HEADER CONTENTS = (Message Size, Time Sent, Send Sleep)
HEADER_FORMAT = "Qdf"
HEADER_SIZE = struct.calcsize(HEADER_FORMAT)

if TYPE_CHECKING:
    from app import App
    from rov_interface import ROVInterface


class ConnectionState(Enum):
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    RECONNECTING = "reconnecting"

    def __str__(self):
        return self.value.title()


@dataclass
class MessageHeader:
    msg_size: int
    recv_time: float
    sleep: float

    @classmethod
    def from_bytes(cls, data: bytes) -> 'MessageHeader':
        """Parse header from bytes with error handling."""
        if len(data) != HEADER_SIZE:
            raise ValueError(f"Invalid header size: expected {HEADER_SIZE}, got {len(data)}")

        try:
            msg_size, recv_time, sleep = struct.unpack(HEADER_FORMAT, data)
            return cls(msg_size, recv_time, sleep)
        except struct.error as e:
            raise ValueError(f"Failed to unpack header: {e}")


class SockStreamRecv(threading.Thread):
    def __init__(self, app: Union["App", "ROVInterface"], addr: str, port: int,
                 on_recv: Callable[[bytes], None],
                 on_connect: Optional[Callable[[], None]] = None,
                 on_disconnect: Optional[Callable[[], None]] = None,
                 on_status_change: Optional[Callable[[], None]] = None,
                 buffer_size: int = 1024,
                 protocol: Literal["tcp", "udp"] = "tcp",
                 timeout: float = 0.5,
                 max_reconnect_attempts: int = -1,
                 reconnect_delay: float = 1.0):
        """
        Initialize socket stream receiver.

        Args:
            max_reconnect_attempts: Maximum reconnection attempts (-1 for infinite)
            reconnect_delay: Delay between reconnection attempts in seconds
        """
        protocol = protocol.lower()
        if protocol not in ["tcp", "udp"]:
            raise ValueError("SockStream Protocol must either be TCP or UDP")

        self._state = ConnectionState.DISCONNECTED
        self._state_lock = threading.Lock()
        self.addr = addr
        self.port = port
        self.on_recv = on_recv
        self.on_connect = on_connect
        self.on_disconnect = on_disconnect
        self.on_status_change = on_status_change
        self.buffer_size = buffer_size
        self.protocol = protocol
        self.app = app
        self.timeout = timeout
        self.max_reconnect_attempts = max_reconnect_attempts
        self.reconnect_delay = reconnect_delay
        self._reconnect_count = 0
        self._shutdown_event = threading.Event()

        # Validate buffer size for UDP
        if protocol == "udp" and buffer_size > 65535:
            print("UDP buffer size reduced to 65535 bytes (UDP maximum)", file=sys.stderr)
            self.buffer_size = 65535

        super().__init__(daemon=True)

    @property
    def state(self) -> ConnectionState:
        with self._state_lock:
            return self._state

    def _set_state(self, new_state: ConnectionState) -> None:
        with self._state_lock:
            old_state = self._state
            self._state = new_state
            if old_state != new_state and self.on_status_change is not None:
                self.on_status_change()

    def is_connected(self) -> bool:
        return self.state == ConnectionState.CONNECTED

    def shutdown(self) -> None:
        """Gracefully shutdown the receiver."""
        self._shutdown_event.set()

    def run(self) -> None:
        print(f"Starting {self}")
        try:
            if self.protocol == "tcp":
                self._run_tcp()
            else:
                self._run_udp()
        except Exception as e:
            print(f"Unexpected error in {self}: {e}", file=sys.stderr)
        finally:
            self._set_state(ConnectionState.DISCONNECTED)
            print(f"Stopped {self}")

    def _should_continue(self) -> bool:
        """Check if the thread should continue running."""
        return not (self.app.closing or self._shutdown_event.is_set())

    def _handle_connection_established(self) -> None:
        """Handle successful connection."""
        if self.state != ConnectionState.CONNECTED:
            self._set_state(ConnectionState.CONNECTED)
            self._reconnect_count = 0
            if self.on_connect:
                try:
                    self.on_connect()
                except Exception as e:
                    print(f"Error in on_connect callback: {e}", file=sys.stderr)

    def _handle_connection_lost(self) -> None:
        """Handle lost connection."""
        if self.state == ConnectionState.CONNECTED:
            self._set_state(ConnectionState.DISCONNECTED)
            if self.on_disconnect:
                try:
                    self.on_disconnect()
                except Exception as e:
                    print(f"Error in on_disconnect callback: {e}", file=sys.stderr)

    def _should_reconnect(self) -> bool:
        """Check if reconnection should be attempted."""
        if self.max_reconnect_attempts == -1:
            return True
        return self._reconnect_count < self.max_reconnect_attempts

    def _wait_before_reconnect(self) -> None:
        """Wait before attempting reconnection."""
        if self._reconnect_count > 0:
            delay = min(self.reconnect_delay * (2 ** min(self._reconnect_count - 1, 5)), 8.0)
            print(f"{self}: Waiting {delay:.1f}s before reconnection attempt {self._reconnect_count + 1}")
            self._shutdown_event.wait(delay)

    def _run_udp(self) -> None:
        """Run UDP receiver with improved error handling."""
        while self._should_continue():
            if not self._should_reconnect():
                print(f"{self}: Maximum reconnection attempts reached", file=sys.stderr)
                break

            self._wait_before_reconnect()
            if not self._should_continue():
                break

            self._reconnect_count += 1
            self._set_state(ConnectionState.CONNECTING)

            sock = None
            try:
                sock = socket(AF_INET, SOCK_DGRAM)
                sock.bind((self.addr, self.port))
                sock.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
                sock.setblocking(False)

                print(f"{self}: UDP socket bound successfully")
                last_msg_time = time.time()

                while self._should_continue():
                    try:
                        payload, client_addr = sock.recvfrom(self.buffer_size)

                        # Handle first message
                        if self.state != ConnectionState.CONNECTED:
                            self._handle_connection_established()
                            print(f"{self}: First message from {client_addr}")

                        # Process message
                        if len(payload) >= HEADER_SIZE:
                            header_data = payload[:HEADER_SIZE]
                            message_payload = payload[HEADER_SIZE:]

                            try:
                                header = MessageHeader.from_bytes(header_data)
                                self._process_message(message_payload, header)
                                last_msg_time = time.time()
                            except ValueError as e:
                                print(f"{self}: Invalid message header: {e}", file=sys.stderr)
                        else:
                            print(f"{self}: Message too short for header", file=sys.stderr)

                    except BlockingIOError:
                        # Check for timeout
                        if (self.state == ConnectionState.CONNECTED and
                                time.time() - last_msg_time > self.timeout):
                            print(f"{self}: UDP timeout after {self.timeout}s", file=sys.stderr)
                            raise TimeoutError("UDP receive timeout")
                        time.sleep(0.001)  # Small sleep to prevent busy waiting

            except (OSError, gaierror, TimeoutError) as e:
                print(f"{self}: UDP error: {e}", file=sys.stderr)
                self._handle_connection_lost()
            except Exception as e:
                print(f"{self}: Unexpected UDP error: {e}", file=sys.stderr)
                self._handle_connection_lost()
            finally:
                if sock:
                    sock.close()

    def _run_tcp(self) -> None:
        """Run TCP receiver with improved error handling."""
        while self._should_continue():
            if not self._should_reconnect():
                print(f"{self}: Maximum reconnection attempts reached", file=sys.stderr)
                break

            self._wait_before_reconnect()
            if not self._should_continue():
                break

            self._reconnect_count += 1
            self._set_state(ConnectionState.CONNECTING)

            server_sock = None
            try:
                server_sock = socket(AF_INET, SOCK_STREAM)
                server_sock.setsockopt(IPPROTO_TCP, TCP_NODELAY, 1)
                server_sock.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
                server_sock.bind((self.addr, self.port))
                server_sock.listen(1)
                server_sock.settimeout(self.timeout)

                print(f"{self}: TCP server listening")

                while self._should_continue():
                    try:
                        conn, client_addr = server_sock.accept()
                        print(f"{self}: TCP connection from {client_addr}")

                        try:
                            conn.settimeout(self.timeout)
                            self._handle_tcp_connection(conn)
                        finally:
                            conn.close()

                    except (TimeoutError, OSError) as e:
                        if not self._should_continue():
                            break
                        # Timeout is expected when waiting for connections
                        continue

            except (OSError, gaierror) as e:
                print(f"{self}: TCP server error: {e}", file=sys.stderr)
                self._handle_connection_lost()
            except Exception as e:
                print(f"{self}: Unexpected TCP error: {e}", exc_info=True, file=sys.stderr)
                self._handle_connection_lost()
            finally:
                if server_sock:
                    server_sock.close()

    def _handle_tcp_connection(self, conn: socket) -> None:
        """Handle individual TCP connection."""
        self._handle_connection_established()

        try:
            buffer = b""
            expecting_header = True
            expected_msg_size = 0

            while self._should_continue():
                try:
                    data = conn.recv(self.buffer_size)
                    if not data:  # Connection closed by client
                        break

                    buffer += data

                    # Process complete messages
                    while len(buffer) >= HEADER_SIZE:
                        if expecting_header:
                            # Parse header
                            header_data = buffer[:HEADER_SIZE]
                            try:
                                header = MessageHeader.from_bytes(header_data)
                                expected_msg_size = header.msg_size
                                buffer = buffer[HEADER_SIZE:]
                                expecting_header = False
                            except ValueError as e:
                                print(f"{self}: Invalid header: {e}", file=sys.stderr)
                                buffer = buffer[1:]  # Skip one byte and try again
                                continue

                        if not expecting_header and len(buffer) >= expected_msg_size:
                            # Extract complete message
                            message_payload = buffer[:expected_msg_size]
                            buffer = buffer[expected_msg_size:]
                            expecting_header = True

                            # Process message
                            self._process_message(message_payload, header)
                        else:
                            break  # Wait for more data

                except (ConnectionError, TimeoutError):
                    break
                except Exception as e:
                    print(f"{self}: TCP receive error: {e}", file=sys.stderr)
                    break

        finally:
            self._handle_connection_lost()

    def _process_message(self, payload: bytes, header: MessageHeader) -> None:
        """Process received message with error handling."""
        try:
            self.on_recv(payload)

            # Handle sleep timing
            if header.sleep > 0:
                time.sleep(header.sleep)

        except Exception as e:
            print(f"{self}: Error processing message: {e}", file=sys.stderr)

    def __repr__(self) -> str:
        return f"SockStreamRecv({self.protocol.upper()} {self.addr}:{self.port})"
