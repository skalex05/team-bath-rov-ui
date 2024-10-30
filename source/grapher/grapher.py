import os

from window import Window

path_dir = os.path.dirname(os.path.realpath(__file__))


class Grapher(Window):
    def __init__(self, *args):
        super().__init__(os.path.join(path_dir, "grapher.ui"), *args)

    def update_data(self):
        # Display latest data for window
        pass
        # print(data.ambient_temperature)
