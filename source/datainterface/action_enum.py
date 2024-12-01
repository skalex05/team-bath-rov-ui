import enum


class ActionEnum(enum.IntEnum):
    RECAL_IMU = enum.auto()
    POWER_ROV = enum.auto()
    POWER_FLOAT = enum.auto()
    REINIT_CAMS = enum.auto()
    MAINTAIN_ROV_DEPTH = enum.auto()
