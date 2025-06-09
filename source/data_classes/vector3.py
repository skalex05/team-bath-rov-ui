from numbers import Number


class Vector3:
    # Just for temporarily representing vector information.
    # Might add more to this later
    def __init__(self, x: float, y: float, z: float):
        if x is None:
            x = 0
        if y is None:
            y = 0
        if z is None:
            z = 0
        self.x = x
        self.y = y
        self.z = z

    def __mul__(self, other: float):
        try:
            other = float(other)
            return Vector3(self.x * other, self.y * other, self.z * other)
        except ValueError:
            raise ValueError(f"Only scalars can be multiplied with Vectors not {type(other)}")

    def __add__(self, other: "Vector3"):
        return Vector3(self.x + other.x, self.y + other.y, self.z + other.z)

    def __repr__(self):
        return f"{self.x:.2f}, {self.y:.2f}, {self.z:.2f}"
