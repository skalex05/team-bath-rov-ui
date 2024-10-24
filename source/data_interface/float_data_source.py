from socket import socket, SOCK_DGRAM, AF_INET
from rov_data import ROVData
import pickle

from float_data import FloatData

# Temporary function to supply data to the UI
# Available Port Numbers: 49152-65535

data_client = socket(AF_INET, SOCK_DGRAM)

float_data = FloatData()

i = 0
while 1:
    try:
        float_data.randomise()
        payload = pickle.dumps(float_data)
        data_client.sendto(payload, ("localhost", 52526))
        i += 1
    except ConnectionError:
        print("ERR")
