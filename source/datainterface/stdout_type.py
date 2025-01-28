import enum


class StdoutType(enum.IntEnum):
    UI = enum.auto()
    UI_ERROR = enum.auto()
    ROV = enum.auto()
    ROV_ERROR = enum.auto()
