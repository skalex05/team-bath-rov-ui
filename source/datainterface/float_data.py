from random import random


def rand_float_range(a: int | float, b: int | float, dp: int = None) -> float:
    return round(a + random() * (b - a), dp)


class FloatData:
    def __init__(self):
        self.float_depth = 0

    def randomise(self) -> None:
        self.float_depth = rand_float_range(0, 3, 2)
