from enum import Enum

class Mode(Enum):
    MASS = "mass"
    INDIVIDUAL = "individual"

current_mode = Mode.MASS
current_session_id = None
