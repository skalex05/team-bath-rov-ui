from random import random, randint

from data_classes.vector3 import Vector3


# Temp function for generating a random float (optionally rounded to 'dp' decimal places)
def rand_float_range(a: int | float, b: int | float, dp: int = None) -> float:
    return round(a + random() * (b - a), dp)


def rand_vector3(a: int | float, b: int | float, dp: int = None) -> Vector3:
    return Vector3(
        rand_float_range(a, b, dp),
        rand_float_range(a, b, dp),
        rand_float_range(a, b, dp)
    )


class ROVData:
    def __init__(self):
        self.attitude = Vector3(0, 0, 0)  # pitch, yaw, roll
        self.angular_acceleration = Vector3(0, 0, 0)
        self.angular_velocity = Vector3(0, 0, 0)
        self.acceleration = Vector3(0, 0, 0)
        self.velocity = Vector3(0, 0, 0)
        self.depth = 0
        self.ambient_temperature = 0
        self.ambient_pressure = 0
        self.internal_temperature = 0
        self.cardinal_direction = 0
        self.grove_water_sensor = 0

    def randomise(self):
        self.ambient_temperature = rand_float_range(23, 27, 2)
        self.ambient_pressure = rand_float_range(100, 130, 2)
