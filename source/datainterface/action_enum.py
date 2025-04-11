import enum


class ActionEnum(enum.IntEnum):
    RECALIBRATE_IMU = enum.auto()
    POWER_ON_ROV = enum.auto()
    POWER_OFF_ROV = enum.auto()
    POWER_ON_FLOAT = enum.auto()
    POWER_OFF_FLOAT = enum.auto()
    REINIT_CAMS = enum.auto()
    MAINTAIN_ROV_DEPTH = enum.auto()
