from float_data import FloatData
from sock_stream_send import SockStreamSend

float_data = FloatData()


def get_float_data():
    global float_data

    float_data.randomise()

    return float_data


data_thread = SockStreamSend(None, "localhost", 52625, 0.05, get_float_data, None)
data_thread.start()
