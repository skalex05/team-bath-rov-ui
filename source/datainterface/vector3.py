class Vector3:
    # Just for temporarily representing vector information.
    # Might add more to this later
    # Could also use
    def __init__(self, x: float, y: float, z: float):
        self.x = x
        self.y = y
        self.z = z

    def __repr__(self):
        return f"{self.x:.2f}, {self.y:.2f}, {self.z:.2f}"
