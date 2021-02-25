import enum

@enum.unique
class CONTROLLERSTATUS(enum.IntEnum):
    """Definition of ControllerModel status codes."""

    DEFAULT = enum.auto()
    INITIALIZED = enum.auto()
    STEP_BEGAN = enum.auto()
    MISSING_TRAINING_DATA = enum.auto()
    MODEL_VALID = enum.auto()
    MODEL_VALIDATION_FAILED = enum.auto()
    OPTIMIZATION_SUCCESSFUL = enum.auto()
    INFEASIBLE_OPTIMIZATION = enum.auto()
    STEP_SUCCESSFUL = enum.auto()
    STEP_FAILED = enum.auto()
    FMU_CRASHED = enum.auto()

    # add other status codes to aid in debugging
