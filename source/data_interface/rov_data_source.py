from socket import socket, SOCK_DGRAM, AF_INET
from rov_data import ROVData
import pickle

# Temporary function to supply data to the UI
# Available Port Numbers: 49152-65535

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
