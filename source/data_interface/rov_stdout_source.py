import pickle
import time
from socket import socket, SOCK_STREAM, AF_INET
from stdout_type import StdoutType
from random import random, choice

# Temporary function to supply data to the UI
# Available Port Numbers: 49152-65535

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
    time.sleep(random()*5)
