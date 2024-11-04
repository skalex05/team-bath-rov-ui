from random import random, randint

from vector3 import Vector3


# Temp function for generating a random float (optionally rounded to 'dp' decimal places)
def rand_float_range(a: int | float, b: int | float, dp: int = None):
    return round(a + random() * (b - a), dp)


def rand_vector3(a: int | float, b: int | float, dp: int = None):
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

        self.main_sonar = 0
        self.FL_sonar = 0
        self.FR_sonar = 0
        self.BR_sonar = 0
        self.BL_sonar = 0

        self.actuator_1 = 0
        self.actuator_2 = 0
        self.actuator_3 = 0
        self.actuator_4 = 0
        self.actuator_5 = 0
        self.actuator_6 = 0

    def randomise(self):
        self.attitude = Vector3(
            rand_float_range(-45, 45, 1),
            rand_float_range(0, 360, 1),
            rand_float_range(-5, 5, 1)
        )

        self.angular_acceleration = rand_vector3(-1, 1, 2)
        self.angular_velocity = rand_vector3(-5, 5, 2)
        self.acceleration = rand_vector3(-1, 1, 2)
        self.velocity = rand_vector3(-5, 5, 2)
        self.depth = rand_float_range(0.5, 2.5, 2)
        self.ambient_temperature = rand_float_range(23, 27, 2)
        self.ambient_pressure = rand_float_range(100, 130, 2)
        self.internal_temperature = rand_float_range(40, 70, 1)

        self.main_sonar = rand_float_range(0, 500, 1)
        self.FL_sonar = rand_float_range(0, 500, 1)
        self.FR_sonar = rand_float_range(0, 500, 1)
        self.BR_sonar = rand_float_range(0, 500, 1)
        self.BL_sonar = rand_float_range(0, 500, 1)

        self.actuator_1 = randint(0, 100)
        self.actuator_2 = randint(0, 100)
        self.actuator_3 = randint(0, 100)
        self.actuator_4 = randint(0, 100)
        self.actuator_5 = randint(0, 100)
        self.actuator_6 = randint(0, 100)
