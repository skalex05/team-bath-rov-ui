import pickle
import time
from time import sleep
from threading import Thread
import cv2


# This function is used to retrieve video frames on the ROV so that they can be sent to the UI.

class VideoStream:
    max_attempts = 5

    def __init__(self, index: int):
        self.camera_feed: cv2.VideoCapture | None = None
        self.init_thread: Thread | None = None
        self.index = index
        self.initialising = False
        self.initialised = False
        self.init_attempts = 0
        self.frame_grabber_thread: Thread | None = None
        self.start_init_camera_feed()

    def start_init_camera_feed(self):
        if self.initialising:
            return
        self.initialising = True
        self.initialised = False
        self.init_attempts = 0
        # Start non-blocking initialisation
        self.init_thread = Thread(target=self.init_camera_feed, daemon=True)
        self.init_thread.start()

    def init_camera_feed(self) -> None:
        print(f"Initialising Cam {self.index + 1}")
        # Assign a VideoCapture device and attempt to read a frame
        self.camera_feed = cv2.VideoCapture(self.index)
        ret = self.camera_feed.grab()
        if ret:
            # VideoCapture Device is working
            # Close an existing frame grabber thread if applicable
            if self.frame_grabber_thread:
                self.frame_grabber_thread.join()

            print(f"Cam {self.index + 1} initialised successfully!")
            self.initialising = False
            self.initialised = True

            # Start a new frame grabber thread to continuously pull frames
            self.frame_grabber_thread = Thread(target=self.poll_camera_frame)
            self.frame_grabber_thread.start()
        else:
            # Failed to read from VideoCapture Device
            print(f"Could not read from Cam {self.index + 1}")
            self.camera_feed = None

            if self.init_attempts < VideoStream.max_attempts:
                self.init_attempts += 1
                print(f"Retrying... Attempt {self.init_attempts}/{self.max_attempts}")
                # Exponential backoff for retries
                sleep(1.5 ** self.init_attempts)
                self.init_camera_feed()
            else:
                self.initialising = False
                print(f"Failed to connect to Cam {self.index + 1}")
            return

    def poll_camera_frame(self) -> None:
        # Continuously grab frame from camera feed while one is available
        while self.initialised:
            if self.camera_feed is None:
                continue
            ret = self.camera_feed.grab()
            if not ret:
                print(f"Could not read from Cam {self.index + 1}")
                self.camera_feed = None
            time.sleep(0)

    def get_camera_frame(self) -> bytes:
        # A function to retrieve and set the most recently grabbed frame
        if not self.camera_feed:
            return pickle.dumps(None)
        ret, frame = self.camera_feed.retrieve()

        if ret:
            encoded, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
            return pickle.dumps(buffer)
        else:
            return pickle.dumps(None)
