from enum import Enum, auto, unique


@unique
class EventType(Enum):
    CREATED = auto()
    MODIFIED = auto()
    DELETED = auto()
    FOUND = auto()
    ERROR = auto()
