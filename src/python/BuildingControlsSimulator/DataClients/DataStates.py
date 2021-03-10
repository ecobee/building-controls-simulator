import enum


@enum.unique
class UNITS(enum.IntEnum):
    """Definition of units for preprocessing to internal unit formats."""

    OTHER = enum.auto()
    CELSIUS = enum.auto()
    FARHENHEIT = enum.auto()
    FARHENHEITx10 = enum.auto()
    RELATIVE_HUMIDITY = enum.auto()
    DATETIME = enum.auto()
    SECONDS = enum.auto()
    WATTS_PER_METER_SQUARED = enum.auto()


@enum.unique
class CHANNELS(enum.IntEnum):
    """Definition of component part of input data for preprocessing to
    internal formats."""

    THERMOSTAT_SETTING = enum.auto()
    EQUIPMENT = enum.auto()
    THERMOSTAT_SENSOR = enum.auto()
    REMOTE_SENSOR = enum.auto()
    WEATHER = enum.auto()
    DATETIME = enum.auto()
    ENERGY_COST = enum.auto()
    SIMULATION = enum.auto()


@enum.unique
class STATES(enum.IntEnum):
    # HVAC states
    DATE_TIME = enum.auto()
    HVAC_MODE = enum.auto()
    SYSTEM_MODE = enum.auto()
    CALENDAR_EVENT = enum.auto()
    SCHEDULE = enum.auto()
    TEMPERATURE_CTRL = enum.auto()
    TEMPERATURE_STP_COOL = enum.auto()
    TEMPERATURE_STP_HEAT = enum.auto()
    HUMIDITY = enum.auto()
    HUMIDITY_EXPECTED_LOW = enum.auto()
    HUMIDITY_EXPECTED_HIGH = enum.auto()
    AUXHEAT1 = enum.auto()
    AUXHEAT2 = enum.auto()
    AUXHEAT3 = enum.auto()
    COMPCOOL1 = enum.auto()
    COMPCOOL2 = enum.auto()
    COMPHEAT1 = enum.auto()
    COMPHEAT2 = enum.auto()
    DEHUMIDIFIER = enum.auto()
    ECONOMIZER = enum.auto()
    FAN = enum.auto()
    HUMIDIFIER = enum.auto()
    VENTILATOR = enum.auto()

    # Sensor states
    THERMOSTAT_TEMPERATURE = enum.auto()
    THERMOSTAT_HUMIDITY = enum.auto()
    THERMOSTAT_MOTION = enum.auto()
    RS1_TEMPERATURE = enum.auto()
    RS2_TEMPERATURE = enum.auto()
    RS3_TEMPERATURE = enum.auto()
    RS4_TEMPERATURE = enum.auto()
    RS5_TEMPERATURE = enum.auto()
    RS6_TEMPERATURE = enum.auto()
    RS7_TEMPERATURE = enum.auto()
    RS8_TEMPERATURE = enum.auto()
    RS9_TEMPERATURE = enum.auto()
    RS10_TEMPERATURE = enum.auto()
    RS1_OCCUPANCY = enum.auto()
    RS2_OCCUPANCY = enum.auto()
    RS3_OCCUPANCY = enum.auto()
    RS4_OCCUPANCY = enum.auto()
    RS5_OCCUPANCY = enum.auto()
    RS6_OCCUPANCY = enum.auto()
    RS7_OCCUPANCY = enum.auto()
    RS8_OCCUPANCY = enum.auto()
    RS9_OCCUPANCY = enum.auto()
    RS10_OCCUPANCY = enum.auto()

    # state estimates
    THERMOSTAT_TEMPERATURE_ESTIMATE = enum.auto()
    THERMOSTAT_HUMIDITY_ESTIMATE = enum.auto()
    THERMOSTAT_MOTION_ESTIMATE = enum.auto()
    RS1_TEMPERATURE_ESTIMATE = enum.auto()
    RS2_TEMPERATURE_ESTIMATE = enum.auto()
    RS3_TEMPERATURE_ESTIMATE = enum.auto()
    RS4_TEMPERATURE_ESTIMATE = enum.auto()
    RS5_TEMPERATURE_ESTIMATE = enum.auto()
    RS6_TEMPERATURE_ESTIMATE = enum.auto()
    RS7_TEMPERATURE_ESTIMATE = enum.auto()
    RS8_TEMPERATURE_ESTIMATE = enum.auto()
    RS9_TEMPERATURE_ESTIMATE = enum.auto()
    RS10_TEMPERATURE_ESTIMATE = enum.auto()

    # Weather states
    OUTDOOR_TEMPERATURE = enum.auto()
    OUTDOOR_RELATIVE_HUMIDITY = enum.auto()
    DIRECT_NORMAL_RADIATION = enum.auto()
    GLOBAL_HORIZONTAL_RADIATION = enum.auto()

    # HVAC actuation states
    FAN_STAGE_ONE = enum.auto()
    FAN_STAGE_TWO = enum.auto()
    FAN_STAGE_THREE = enum.auto()
    STEP_STATUS = enum.auto()
    SIMULATION_TIME = enum.auto()

    # final state enum value
    MAX_VALUE = enum.auto()
