import pickle
import struct
import sys
import threading
from socket import socket, AF_INET, SOCK_STREAM, SOCK_DGRAM, SOL_SOCKET, SO_REUSEADDR, IPPROTO_TCP, TCP_NODELAY, \
    gaierror
import time
from typing import TYPE_CHECKING, Literal, Any, Union, Optional, Callable
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


class SockStreamSend(threading.Thread):
    def __init__(self, app: Union["App", "ROVInterface"], addr: str, port: int, sleep: float,
                 get_data: Callable[[], bytes],
                 on_connect: Optional[Callable[[], None]] = None,
                 on_disconnect: Optional[Callable[[], None]] = None,
                 on_status_change: Optional[Callable[[], None]] = None,
                 protocol: Literal["tcp", "udp"] = "tcp",
                 timeout: float = 0.5,
                 max_reconnect_attempts: int = -1,
                 reconnect_delay: float = 1.0):
        """
        Initialize socket stream sender.

        Args:
            max_reconnect_attempts: Maximum reconnection attempts (-1 for infinite)
            reconnect_delay: Delay between reconnection attempts in seconds
        """
        protocol = protocol.lower()
        if protocol not in ["tcp", "udp"]:
            raise ValueError("SockStream Protocol must either be TCP or UDP")

        self.app = app
        self._state = ConnectionState.DISCONNECTED
        self._state_lock = threading.Lock()
        self.addr = addr
        self.port = port
        self.get_data = get_data
        self.on_connect = on_connect
        self.on_disconnect = on_disconnect
        self.on_status_change = on_status_change
        self.sleep = sleep
        self.protocol = protocol
        self.timeout = timeout
        self.max_reconnect_attempts = max_reconnect_attempts
        self.reconnect_delay = reconnect_delay
        self._reconnect_count = 0
        self._shutdown_event = threading.Event()

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
        """Gracefully shutdown the sender."""
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
            print(f"{self}: Connected!")
            if self.on_connect:
                try:
                    self.on_connect()
                except Exception as e:
                    print(f"Error in on_connect callback: {e}", file=sys.stderr)

    def _handle_connection_lost(self) -> None:
        """Handle lost connection."""
        if self.state == ConnectionState.CONNECTED:
            print(f"{self}: Connection Lost!")
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
        """Wait before attempting reconnection with exponential backoff."""
        if self._reconnect_count > 0:
            delay = min(self.reconnect_delay * (2 ** min(self._reconnect_count - 1, 5)), 8.0)
            print(f"{self}: Waiting {delay:.1f}s before reconnection attempt {self._reconnect_count + 1}")
            self._shutdown_event.wait(delay)

    def _get_data_safely(self) -> Optional[bytes]:
        """Safely get data from the data function."""
        try:
            data = self.get_data()
            return data
        except Exception as e:
            print(f"{self}: Failed to get data: {e}", file=sys.stderr)
            return None

    def _create_payload(self, data: bytes) -> bytes:
        """Create payload with header."""
        header = struct.pack(HEADER_FORMAT, len(data), time.time(), self.sleep)
        return header + data

    def _run_udp(self) -> None:
        """Run UDP sender with improved error handling."""
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
                sock.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
                sock.settimeout(self.timeout)

                print(f"{self}: UDP socket created")
                first_send = True

                while self._should_continue():
                    start_time = time.time()

                    # Get data
                    data = self._get_data_safely()
                    if data is None:
                        time.sleep(0.001)  # Small sleep to prevent busy waiting
                        continue

                    try:
                        payload = self._create_payload(data)
                        sock.sendto(payload, (self.addr, self.port))

                        # Handle first successful send
                        if first_send:
                            self._handle_connection_established()
                            first_send = False
                            print(f"{self}: First UDP message sent to {self.addr}:{self.port}")

                        # Sleep timing
                        elapsed = time.time() - start_time
                        if elapsed < self.sleep:
                            sleep_time = self.sleep - elapsed
                            if self._shutdown_event.wait(sleep_time):
                                break  # Shutdown requested

                    except (ConnectionError, TimeoutError, OSError) as e:
                        print(f"{self}: UDP send error: {e}", file=sys.stderr)
                        raise  # Re-raise to trigger reconnection

            except (OSError, gaierror) as e:
                print(f"{self}: UDP error: {e}", file=sys.stderr)
                self._handle_connection_lost()
            except Exception as e:
                print(f"{self}: Unexpected UDP error: {e}", file=sys.stderr)
                self._handle_connection_lost()
            finally:
                if sock:
                    sock.close()

    def _run_tcp(self) -> None:
        """Run TCP sender with improved error handling."""
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
                sock = socket(AF_INET, SOCK_STREAM)
                sock.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
                sock.setsockopt(IPPROTO_TCP, TCP_NODELAY, 1)
                sock.settimeout(self.timeout)

                print(f"{self}: Attempting TCP connection to {self.addr}:{self.port}")
                sock.connect((self.addr, self.port))

                self._handle_connection_established()
                print(f"{self}: TCP connected to {self.addr}:{self.port}")

                # Main sending loop
                while self._should_continue():
                    start_time = time.time()

                    # Get data
                    data = self._get_data_safely()
                    if data is None:
                        time.sleep(0.001)  # Small sleep to prevent busy waiting
                        continue

                    try:
                        payload = self._create_payload(data)
                        sock.sendall(payload)

                        # Sleep timing
                        elapsed = time.time() - start_time
                        if elapsed < self.sleep:
                            sleep_time = self.sleep - elapsed
                            if self._shutdown_event.wait(sleep_time):
                                break  # Shutdown requested

                    except (ConnectionError, TimeoutError, OSError) as e:
                        print(f"{self}: TCP send error: {e}", file=sys.stderr)
                        raise  # Re-raise to trigger reconnection

            except (ConnectionError, TimeoutError, gaierror) as e:
                print(f"{self}: TCP connection failed: {e}")
                self._handle_connection_lost()
            except Exception as e:
                print(f"{self}: Unexpected TCP error: {e}")
                self._handle_connection_lost()
            finally:
                if sock:
                    sock.close()
                    print(f"{self}: TCP socket closed")

    def __repr__(self) -> str:
        return f"SockStreamSend({self.protocol.upper()} {self.addr}:{self.port})"


def SockSend(app: Union["App", "ROVInterface"], addr: str, port: int, msg: Any,
             max_retries: int = 5, timeout: float = 0.5) -> bool:
    """
    Send a single message to a SockStreamRecv.

    Args:
        app: Application instance
        addr: Target address
        port: Target port
        msg: Message to send (will be pickled)
        max_retries: Maximum retry attempts
        timeout: Connection timeout

    Returns:
        bool: True if message was sent successfully, False otherwise
    """
    try:
        bytes_to_send = pickle.dumps(msg)
    except Exception as e:
        print(f"Failed to pickle message: {e}", file=sys.stderr)
        return False

    # Create payload with header (sleep = -1 indicates single message)
    header = struct.pack(HEADER_FORMAT, len(bytes_to_send), time.time(), -1)
    payload = header + bytes_to_send

    for attempt in range(max_retries):
        if app.closing:
            print("App is closing, aborting SockSend", file=sys.__stdout__)
            return False

        sock = None
        try:
            sock = socket(AF_INET, SOCK_STREAM)
            sock.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
            sock.setsockopt(IPPROTO_TCP, TCP_NODELAY, 1)
            sock.settimeout(timeout)

            sock.connect((addr, port))
            sock.sendall(payload)

            return True

        except (ConnectionError, TimeoutError, gaierror) as e:
            pass
        except Exception as e:
            print(f"Unexpected error in SockSend to {addr}:{port}: {e}", file=sys.__stderr__)
        finally:
            if sock:
                sock.close()

    print(f"SockSend failed after {max_retries} attempts to {addr}:{port}", file=sys.stderr)
    return False
