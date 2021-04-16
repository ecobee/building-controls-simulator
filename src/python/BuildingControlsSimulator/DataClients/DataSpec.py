import numpy as np
import pandas as pd
import logging

import attr

from BuildingControlsSimulator.Conversions.Conversions import Conversions
from BuildingControlsSimulator.DataClients.DataStates import (
    UNITS,
    CHANNELS,
    STATES,
)

logger = logging.getLogger(__name__)


def spec_unit_conversion(df, src_spec, dest_spec):
    """This method must be able to evaluate multiple sources should
    a channel be composed from multiple sources."""
    for k, v in src_spec.full.spec.items():
        if k in df.columns:
            src_unit = v["unit"]
            # permutations on Internal spec usage
            dest_unit = None
            if isinstance(dest_spec, Internal):
                dest_unit = dest_spec.full.spec[v["internal_state"]]["unit"]
            elif isinstance(src_spec, Internal):
                for d_k, d_v in dest_spec.full.spec.items():
                    if d_v["internal_state"] == k:
                        dest_unit = d_v["unit"]
            else:
                for d_k, d_v in dest_spec.full.spec.items():
                    if d_v["internal_state"] == v["internal_state"]:
                        dest_unit = d_v["unit"]

            if dest_unit and src_unit != dest_unit:
                if (src_unit == UNITS.FARHENHEIT) and (dest_unit == UNITS.CELSIUS):
                    df[k] = Conversions.F2C(df[k])
                elif (src_unit == UNITS.CELSIUS) and (dest_unit == UNITS.FARHENHEIT):
                    df[k] = Conversions.C2F(df[k])
                elif (src_unit == UNITS.FARHENHEITx10) and (
                    dest_unit == UNITS.FARHENHEIT
                ):
                    df[k] = df[k] / 10.0
                elif (src_unit == UNITS.FARHENHEITx10) and (dest_unit == UNITS.CELSIUS):
                    df[k] = Conversions.F2C(df[k] / 10.0)
                elif (src_unit == UNITS.CELSIUS) and (dest_unit == UNITS.FARHENHEITx10):
                    df[k] = Conversions.C2F(df[k]) * 10.0
                else:
                    logger.error(
                        "Unsupported conversion: {} to {}".format(
                            src_unit,
                            dest_unit,
                        )
                    )
    return df


def get_dtype_mapper(df_cols, dest_spec, src_nullable=False, dest_nullable=False):
    # we only need to consider the destination spec
    dtype_mapper = {
        k: v["dtype"] for k, v in dest_spec.full.spec.items() if k in df_cols
    }

    # convert between nullable columns and non-nullable for compatability
    if dest_nullable:
        for k, v in dtype_mapper.items():
            if v == "bool":
                dtype_mapper[k] = "boolean"
            elif v == "int8":
                dtype_mapper[k] = "Int8"
            elif v == "int16":
                dtype_mapper[k] = "Int16"
            elif v == "int32":
                dtype_mapper[k] = "Int32"
            elif v == "int64":
                dtype_mapper[k] = "Int64"
    else:
        for k, v in dtype_mapper.items():
            if v == "boolean":
                dtype_mapper[k] = "bool"
            elif v == "Int8":
                dtype_mapper[k] = "int8"
            elif v == "Int16":
                dtype_mapper[k] = "int16"
            elif v == "Int32":
                dtype_mapper[k] = "int32"
            elif v == "Int64":
                dtype_mapper[k] = "int64"

    return dtype_mapper


def get_rename_mapper(src_spec, dest_spec):
    # permutations on Internal spec usage
    if isinstance(dest_spec, Internal):
        rename_mapper = {k: v["internal_state"] for k, v in src_spec.full.spec.items()}
    elif isinstance(src_spec, Internal):
        rename_mapper = {}
        for k, v in src_spec.full.spec.items():
            for d_k, d_v in dest_spec.full.spec.items():
                if d_v["internal_state"] == k:
                    rename_mapper.update({k: d_k})
    else:
        rename_mapper = {}
        for k, v in src_spec.full.spec.items():
            for d_k, d_v in dest_spec.full.spec.items():
                if d_v["internal_state"] == v["internal_state"]:
                    rename_mapper.update({k: d_k})

    return rename_mapper


def project_spec_keys(src_spec, dest_spec):
    """Return the keys in src_spec that have keys in dest_spec with same state"""
    # permutations on Internal spec usage
    if type(src_spec) == type(dest_spec):
        return list(src_spec.full.spec.keys())

    projection = []
    if isinstance(dest_spec, Internal):
        dest_states = list(dest_spec.full.spec.keys())
        projection = [
            k
            for k, v in src_spec.full.spec.items()
            if v["internal_state"] in dest_states
        ]
    elif isinstance(src_spec, Internal):
        dest_states = [
            d_v["internal_state"] for d_k, d_v in dest_spec.full.spec.items()
        ]
        projection = [k for k in src_spec.full.spec.keys() if k in dest_states]
    else:
        dest_states = [
            d_v["internal_state"] for d_k, d_v in dest_spec.full.spec.items()
        ]
        projection = [
            k
            for k, v in src_spec.full.spec.items()
            if v["internal_state"] in dest_states
        ]

    return projection


def convert_spec(
    df, src_spec, dest_spec, src_nullable=False, dest_nullable=False, copy=False
):
    # src_nullable: whether to use nullable int types
    # dest_nullable: whether to use nullable int types
    if type(src_spec) == type(dest_spec):
        logger.info("convert_spec: src_spec is equal to dest_spec.")
        return df

    if copy:
        _df = df.copy(deep=True)
    else:
        _df = df

    # drop columns not in dest_spec
    _df = _df.drop(
        axis="columns",
        columns=[
            _col
            for _col in _df.columns
            if _col not in project_spec_keys(src_spec, dest_spec)
        ],
    )

    _df = spec_unit_conversion(
        df=_df,
        src_spec=src_spec,
        dest_spec=dest_spec,
    )
    _df = _df.rename(columns=get_rename_mapper(src_spec=src_spec, dest_spec=dest_spec))

    _df = _df.astype(
        dtype=get_dtype_mapper(
            df_cols=_df.columns,
            dest_spec=dest_spec,
            src_nullable=src_nullable,
            dest_nullable=dest_nullable,
        ),
    )
    _df = _df.sort_values(dest_spec.datetime_column, ascending=True)
    return _df


@attr.s(kw_only=True, frozen=True, slots=True)
class Spec:
    spec = attr.ib()
    null_check_columns = attr.ib()
    datetime_column = attr.ib()

    @spec.validator
    def dtypes_are_pandas(self, attribute, value):
        supported_dtypes = [
            "bool",
            "boolean",
            "string",
            "Float32",
            "float32",
            "Float64",
            "float64",
            "Int8",
            "Int16",
            "Int32",
            "Int64",
            "int8",
            "int16",
            "int32",
            "int64",
            "UInt8",
            "UInt16",
            "UInt32",
            "UInt64",
            "category",
            "datetime64[ns, utc]",
        ]
        for k, v in value.items():
            if v["dtype"] not in supported_dtypes:
                raise ValueError(
                    f"Spec failed validation. Invalid dtype={v['dtype']} for key={k}."
                )

    @property
    def columns(self):
        return list(self.spec.keys())


class Internal:
    """Definition of internal data fields and types.
    For details of string dtype aliases see:
    https://pandas.pydata.org/pandas-docs/stable/user_guide/basics.html#basics-dtypes

    Note: Float16 is software simulated and often slower (with less memory usage)
    """

    N_ROOM_SENSORS = 10
    datetime_column = STATES.DATE_TIME
    data_period_seconds = 300

    def __init__(self):

        # dtype [ns, TZ] is used to represent the known TZ of data
        # do not need Enum value for only one column
        self.datetime = Spec(
            datetime_column=self.datetime_column,
            null_check_columns=[self.datetime_column],
            spec={
                self.datetime_column: {
                    "name": "date_time",
                    "dtype": "datetime64[ns, utc]",
                    "channel": CHANNELS.DATETIME,
                    "unit": UNITS.DATETIME,
                },
            },
        )

        self.thermostat = Spec(
            datetime_column=self.datetime_column,
            null_check_columns=[STATES.HVAC_MODE],
            spec={
                STATES.HVAC_MODE: {
                    "name": "hvac_mode",
                    "dtype": "category",
                    "channel": CHANNELS.THERMOSTAT_SETTING,
                    "unit": UNITS.OTHER,
                },
                STATES.SYSTEM_MODE: {
                    "name": "system_mode",
                    "dtype": "category",
                    "channel": CHANNELS.THERMOSTAT_SETTING,
                    "unit": UNITS.OTHER,
                },
                STATES.CALENDAR_EVENT: {
                    "name": "calendar_event",
                    "dtype": "category",
                    "channel": CHANNELS.THERMOSTAT_SETTING,
                    "unit": UNITS.OTHER,
                },
                STATES.SCHEDULE: {
                    "name": "schedule",
                    "dtype": "category",
                    "channel": CHANNELS.THERMOSTAT_SETTING,
                    "unit": UNITS.OTHER,
                },
                STATES.TEMPERATURE_CTRL: {
                    "name": "temperature_ctrl",
                    "dtype": "float32",
                    "channel": CHANNELS.THERMOSTAT_SETTING,
                    "unit": UNITS.CELSIUS,
                },
                STATES.TEMPERATURE_STP_COOL: {
                    "name": "temperature_stp_cool",
                    "dtype": "float32",
                    "channel": CHANNELS.THERMOSTAT_SETTING,
                    "unit": UNITS.CELSIUS,
                },
                STATES.TEMPERATURE_STP_HEAT: {
                    "name": "temperature_stp_heat",
                    "dtype": "float32",
                    "channel": CHANNELS.THERMOSTAT_SETTING,
                    "unit": UNITS.CELSIUS,
                },
                STATES.HUMIDITY: {
                    "name": "humidity",
                    "dtype": "float32",
                    "channel": CHANNELS.THERMOSTAT_SETTING,
                    "unit": UNITS.RELATIVE_HUMIDITY,
                },
                STATES.HUMIDITY_EXPECTED_LOW: {
                    "name": "humidity_expected_low",
                    "dtype": "float32",
                    "channel": CHANNELS.THERMOSTAT_SETTING,
                    "unit": UNITS.RELATIVE_HUMIDITY,
                },
                STATES.HUMIDITY_EXPECTED_HIGH: {
                    "name": "humidity_expected_high",
                    "dtype": "float32",
                    "channel": CHANNELS.THERMOSTAT_SETTING,
                    "unit": UNITS.RELATIVE_HUMIDITY,
                },
            },
        )

        self.equipment = Spec(
            datetime_column=self.datetime_column,
            null_check_columns=[STATES.HVAC_MODE],
            spec={
                STATES.AUXHEAT1: {
                    "name": "auxHeat1",
                    "dtype": "int16",
                    "channel": CHANNELS.EQUIPMENT,
                    "unit": UNITS.SECONDS,
                },
                STATES.AUXHEAT2: {
                    "name": "auxHeat2",
                    "dtype": "int16",
                    "channel": CHANNELS.EQUIPMENT,
                    "unit": UNITS.SECONDS,
                },
                STATES.AUXHEAT3: {
                    "name": "auxHeat3",
                    "dtype": "int16",
                    "channel": CHANNELS.EQUIPMENT,
                    "unit": UNITS.SECONDS,
                },
                STATES.COMPCOOL1: {
                    "name": "compCool1",
                    "dtype": "int16",
                    "channel": CHANNELS.EQUIPMENT,
                    "unit": UNITS.SECONDS,
                },
                STATES.COMPCOOL2: {
                    "name": "compCool2",
                    "dtype": "int16",
                    "channel": CHANNELS.EQUIPMENT,
                    "unit": UNITS.SECONDS,
                },
                STATES.COMPHEAT1: {
                    "name": "compHeat1",
                    "dtype": "int16",
                    "channel": CHANNELS.EQUIPMENT,
                    "unit": UNITS.SECONDS,
                },
                STATES.COMPHEAT2: {
                    "name": "compHeat2",
                    "dtype": "int16",
                    "channel": CHANNELS.EQUIPMENT,
                    "unit": UNITS.SECONDS,
                },
                STATES.DEHUMIDIFIER: {
                    "name": "dehumidifier",
                    "dtype": "int16",
                    "channel": CHANNELS.EQUIPMENT,
                    "unit": UNITS.SECONDS,
                },
                STATES.ECONOMIZER: {
                    "name": "economizer",
                    "dtype": "int16",
                    "channel": CHANNELS.EQUIPMENT,
                    "unit": UNITS.SECONDS,
                },
                STATES.FAN: {
                    "name": "fan",
                    "dtype": "int16",
                    "channel": CHANNELS.EQUIPMENT,
                    "unit": UNITS.SECONDS,
                },
                STATES.FAN_STAGE_ONE: {
                    "name": "fan1",
                    "dtype": "int16",
                    "channel": CHANNELS.EQUIPMENT,
                    "unit": UNITS.SECONDS,
                },
                STATES.FAN_STAGE_TWO: {
                    "name": "fan2",
                    "dtype": "int16",
                    "channel": CHANNELS.EQUIPMENT,
                    "unit": UNITS.SECONDS,
                },
                STATES.FAN_STAGE_THREE: {
                    "name": "fan3",
                    "dtype": "int16",
                    "channel": CHANNELS.EQUIPMENT,
                    "unit": UNITS.SECONDS,
                },
                STATES.HUMIDIFIER: {
                    "name": "humidifier",
                    "dtype": "int16",
                    "channel": CHANNELS.EQUIPMENT,
                    "unit": UNITS.SECONDS,
                },
                STATES.VENTILATOR: {
                    "name": "ventilator",
                    "dtype": "int16",
                    "channel": CHANNELS.EQUIPMENT,
                    "unit": UNITS.SECONDS,
                },
            },
        )

        self.sensors = Spec(
            datetime_column=self.datetime_column,
            null_check_columns=[STATES.THERMOSTAT_TEMPERATURE],
            spec={
                STATES.THERMOSTAT_TEMPERATURE: {
                    "name": "thermostat_temperature",
                    "dtype": "float32",
                    "channel": CHANNELS.THERMOSTAT_SENSOR,
                    "unit": UNITS.CELSIUS,
                },
                STATES.THERMOSTAT_TEMPERATURE_ESTIMATE: {
                    "name": "thermostat_temperature_estimate",
                    "dtype": "float32",
                    "channel": CHANNELS.THERMOSTAT_SENSOR,
                    "unit": UNITS.CELSIUS,
                },
                STATES.THERMOSTAT_HUMIDITY: {
                    "name": "thermostat_humidity",
                    "dtype": "float32",
                    "channel": CHANNELS.THERMOSTAT_SENSOR,
                    "unit": UNITS.RELATIVE_HUMIDITY,
                },
                STATES.THERMOSTAT_HUMIDITY_ESTIMATE: {
                    "name": "thermostat_humidity_estimate",
                    "dtype": "float32",
                    "channel": CHANNELS.THERMOSTAT_SENSOR,
                    "unit": UNITS.RELATIVE_HUMIDITY,
                },
                STATES.THERMOSTAT_MOTION: {
                    "name": "thermostat_motion",
                    "dtype": "boolean",
                    "channel": CHANNELS.THERMOSTAT_SENSOR,
                    "unit": UNITS.OTHER,
                },
                STATES.THERMOSTAT_MOTION_ESTIMATE: {
                    "name": "thermostat_motion_estimate",
                    "dtype": "boolean",
                    "channel": CHANNELS.THERMOSTAT_SENSOR,
                    "unit": UNITS.OTHER,
                },
                **{
                    STATES["RS{}_TEMPERATURE".format(i)]: {
                        "name": "rs{}_temperature".format(i),
                        "dtype": "float32",
                        "channel": CHANNELS.REMOTE_SENSOR,
                        "unit": UNITS.CELSIUS,
                    }
                    for i in range(1, self.N_ROOM_SENSORS + 1)
                },
                **{
                    STATES["RS{}_TEMPERATURE_ESTIMATE".format(i)]: {
                        "name": "rs{}_temperature_estimate".format(i),
                        "dtype": "float32",
                        "channel": CHANNELS.REMOTE_SENSOR,
                        "unit": UNITS.CELSIUS,
                    }
                    for i in range(1, self.N_ROOM_SENSORS + 1)
                },
                **{
                    STATES["RS{}_OCCUPANCY".format(i)]: {
                        "name": "rs{}_occupancy".format(i),
                        "dtype": "boolean",
                        "channel": CHANNELS.REMOTE_SENSOR,
                        "unit": UNITS.OTHER,
                    }
                    for i in range(1, self.N_ROOM_SENSORS + 1)
                },
            },
        )

        self.weather = Spec(
            datetime_column=self.datetime_column,
            null_check_columns=[STATES.OUTDOOR_TEMPERATURE],
            spec={
                STATES.OUTDOOR_TEMPERATURE: {
                    "name": "outdoor_temperature",
                    "dtype": "float32",
                    "channel": CHANNELS.WEATHER,
                    "unit": UNITS.CELSIUS,
                },
                STATES.OUTDOOR_RELATIVE_HUMIDITY: {
                    "name": "outdoor_relative_humidity",
                    "dtype": "float32",
                    "channel": CHANNELS.WEATHER,
                    "unit": UNITS.RELATIVE_HUMIDITY,
                },
                STATES.DIRECT_NORMAL_IRRADIANCE: {
                    "name": "direct_normal_radiation",
                    "dtype": "float32",
                    "channel": CHANNELS.WEATHER,
                    "unit": UNITS.WATTS_PER_METER_SQUARED,
                },
                STATES.GLOBAL_HORIZONTAL_IRRADIANCE: {
                    "name": "global_horizontal_radiation",
                    "dtype": "float32",
                    "channel": CHANNELS.WEATHER,
                    "unit": UNITS.WATTS_PER_METER_SQUARED,
                },
                STATES.DIFFUSE_HORIZONTAL_IRRADIANCE: {
                    "name": "diffuse_horizontal_radiation",
                    "dtype": "float32",
                    "channel": CHANNELS.WEATHER,
                    "unit": UNITS.WATTS_PER_METER_SQUARED,
                },
            },
        )

        self.simulation = Spec(
            datetime_column=self.datetime_column,
            null_check_columns=[STATES.SIMULATION_TIME],
            spec={
                STATES.STEP_STATUS: {
                    "name": "status",
                    "dtype": "Int8",
                    "channel": CHANNELS.SIMULATION,
                    "unit": UNITS.OTHER,
                },
                STATES.SIMULATION_TIME: {
                    "name": "simulation_time_seconds",
                    "dtype": "Int64",
                    "channel": CHANNELS.SIMULATION,
                    "unit": UNITS.SECONDS,
                },
            },
        )

        self.full = Spec(
            datetime_column=self.datetime_column,
            null_check_columns=self.datetime.null_check_columns
            + self.thermostat.null_check_columns
            + self.equipment.null_check_columns
            + self.sensors.null_check_columns
            + self.weather.null_check_columns,
            spec={
                **self.datetime.spec,
                **self.thermostat.spec,
                **self.equipment.spec,
                **self.sensors.spec,
                **self.weather.spec,
                **self.simulation.spec,
            },
        )

    def __setattr__(self, name, value):
        if hasattr(self, name):
            raise AttributeError("Cannot change specification dynamically.")
        else:
            self.__dict__[name] = value

    @staticmethod
    def intersect_columns(_df_columns, _spec):
        return [c for c in _df_columns if c in _spec.keys()]

    def get_empty_df(self):
        return pd.DataFrame([], columns=self.full.columns)


class FlatFilesSpec:
    datetime_format = "utc"
    datetime_column = "date_time"
    N_ROOM_SENSORS = 10
    data_period_seconds = 300

    def __init__(self):
        self.datetime = Spec(
            datetime_column=self.datetime_column,
            null_check_columns=self.datetime_column,
            spec={
                self.datetime_column: {
                    "internal_state": STATES.DATE_TIME,
                    "dtype": "datetime64[ns, utc]",
                    "channel": CHANNELS.DATETIME,
                    "unit": UNITS.DATETIME,
                },
            },
        )
        self.thermostat = Spec(
            datetime_column=self.datetime_column,
            null_check_columns="HvacMode",
            spec={
                "HvacMode": {
                    "internal_state": STATES.HVAC_MODE,
                    "dtype": "category",
                    "channel": CHANNELS.THERMOSTAT_SETTING,
                    "unit": UNITS.OTHER,
                },
                "SystemMode": {
                    "internal_state": STATES.SYSTEM_MODE,
                    "dtype": "category",
                    "channel": CHANNELS.THERMOSTAT_SETTING,
                    "unit": UNITS.OTHER,
                },
                "CalendarEvent": {
                    "internal_state": STATES.CALENDAR_EVENT,
                    "dtype": "category",
                    "channel": CHANNELS.THERMOSTAT_SETTING,
                    "unit": UNITS.OTHER,
                },
                "Climate": {
                    "internal_state": STATES.SCHEDULE,
                    "dtype": "category",
                    "channel": CHANNELS.THERMOSTAT_SETTING,
                    "unit": UNITS.OTHER,
                },
                "Temperature_ctrl": {
                    "internal_state": STATES.TEMPERATURE_CTRL,
                    "dtype": "float32",
                    "channel": CHANNELS.THERMOSTAT_SETTING,
                    "unit": UNITS.FARHENHEITx10,
                },
                "TemperatureExpectedCool": {
                    "internal_state": STATES.TEMPERATURE_STP_COOL,
                    "dtype": "float32",
                    "channel": CHANNELS.THERMOSTAT_SETTING,
                    "unit": UNITS.FARHENHEITx10,
                },
                "TemperatureExpectedHeat": {
                    "internal_state": STATES.TEMPERATURE_STP_HEAT,
                    "dtype": "float32",
                    "channel": CHANNELS.THERMOSTAT_SETTING,
                    "unit": UNITS.FARHENHEITx10,
                },
                "Humidity": {
                    "internal_state": STATES.HUMIDITY,
                    "dtype": "float32",
                    "channel": CHANNELS.THERMOSTAT_SETTING,
                    "unit": UNITS.RELATIVE_HUMIDITY,
                },
                "HumidityExpectedLow": {
                    "internal_state": STATES.HUMIDITY_EXPECTED_LOW,
                    "dtype": "float32",
                    "channel": CHANNELS.THERMOSTAT_SETTING,
                    "unit": UNITS.RELATIVE_HUMIDITY,
                },
                "HumidityExpectedHigh": {
                    "internal_state": STATES.HUMIDITY_EXPECTED_HIGH,
                    "dtype": "float32",
                    "channel": CHANNELS.THERMOSTAT_SETTING,
                    "unit": UNITS.RELATIVE_HUMIDITY,
                },
            },
        )

        self.equipment = Spec(
            datetime_column=self.datetime_column,
            null_check_columns="HvacMode",
            spec={
                "auxHeat1": {
                    "internal_state": STATES.AUXHEAT1,
                    "dtype": "int16",
                    "channel": CHANNELS.EQUIPMENT,
                    "unit": UNITS.SECONDS,
                },
                "auxHeat2": {
                    "internal_state": STATES.AUXHEAT2,
                    "dtype": "int16",
                    "channel": CHANNELS.EQUIPMENT,
                    "unit": UNITS.SECONDS,
                },
                "auxHeat3": {
                    "internal_state": STATES.AUXHEAT3,
                    "dtype": "int16",
                    "channel": CHANNELS.EQUIPMENT,
                    "unit": UNITS.SECONDS,
                },
                "compCool1": {
                    "internal_state": STATES.COMPCOOL1,
                    "dtype": "int16",
                    "channel": CHANNELS.EQUIPMENT,
                    "unit": UNITS.SECONDS,
                },
                "compCool2": {
                    "internal_state": STATES.COMPCOOL2,
                    "dtype": "int16",
                    "channel": CHANNELS.EQUIPMENT,
                    "unit": UNITS.SECONDS,
                },
                "compHeat1": {
                    "internal_state": STATES.COMPHEAT1,
                    "dtype": "int16",
                    "channel": CHANNELS.EQUIPMENT,
                    "unit": UNITS.SECONDS,
                },
                "compHeat2": {
                    "internal_state": STATES.COMPHEAT2,
                    "dtype": "int16",
                    "channel": CHANNELS.EQUIPMENT,
                    "unit": UNITS.SECONDS,
                },
                "dehumidifier": {
                    "internal_state": STATES.DEHUMIDIFIER,
                    "dtype": "int16",
                    "channel": CHANNELS.EQUIPMENT,
                    "unit": UNITS.SECONDS,
                },
                "economizer": {
                    "internal_state": STATES.ECONOMIZER,
                    "dtype": "int16",
                    "channel": CHANNELS.EQUIPMENT,
                    "unit": UNITS.SECONDS,
                },
                "fan": {
                    "internal_state": STATES.FAN,
                    "dtype": "int16",
                    "channel": CHANNELS.EQUIPMENT,
                    "unit": UNITS.SECONDS,
                },
                "humidifier": {
                    "internal_state": STATES.HUMIDIFIER,
                    "dtype": "int16",
                    "channel": CHANNELS.EQUIPMENT,
                    "unit": UNITS.SECONDS,
                },
                "ventilator": {
                    "internal_state": STATES.VENTILATOR,
                    "dtype": "int16",
                    "channel": CHANNELS.EQUIPMENT,
                    "unit": UNITS.SECONDS,
                },
            },
        )

        self.sensors = Spec(
            datetime_column=self.datetime_column,
            null_check_columns="thermostat_temperature",
            spec={
                "SensorTemp000": {
                    "internal_state": STATES.THERMOSTAT_TEMPERATURE,
                    "dtype": "float32",
                    "channel": CHANNELS.THERMOSTAT_SENSOR,
                    "unit": UNITS.FARHENHEITx10,
                },
                "SensorHum000": {
                    "internal_state": STATES.THERMOSTAT_HUMIDITY,
                    "dtype": "float32",
                    "channel": CHANNELS.THERMOSTAT_SENSOR,
                    "unit": UNITS.RELATIVE_HUMIDITY,
                },
                "SensorOcc000": {
                    "internal_state": STATES.THERMOSTAT_MOTION,
                    "dtype": "boolean",
                    "channel": CHANNELS.THERMOSTAT_SENSOR,
                    "unit": UNITS.OTHER,
                },
                **{
                    "SensorTemp1{}".format(str(i).zfill(2)): {
                        "internal_state": STATES["RS{}_TEMPERATURE".format(i)],
                        "dtype": "float32",
                        "channel": CHANNELS.REMOTE_SENSOR,
                        "unit": UNITS.FARHENHEITx10,
                    }
                    for i in range(1, self.N_ROOM_SENSORS + 1)
                },
                **{
                    "SensorOcc1{}".format(str(i).zfill(2)): {
                        "internal_state": STATES["RS{}_OCCUPANCY".format(i)],
                        "dtype": "boolean",
                        "channel": CHANNELS.REMOTE_SENSOR,
                        "unit": UNITS.OTHER,
                    }
                    for i in range(1, self.N_ROOM_SENSORS + 1)
                },
            },
        )

        self.weather = Spec(
            datetime_column=self.datetime_column,
            null_check_columns="Temperature",
            spec={
                "Temperature": {
                    "internal_state": STATES.OUTDOOR_TEMPERATURE,
                    "dtype": "float32",
                    "channel": CHANNELS.WEATHER,
                    "unit": UNITS.FARHENHEITx10,
                },
                "RelativeHumidity": {
                    "internal_state": STATES.OUTDOOR_RELATIVE_HUMIDITY,
                    "dtype": "float32",
                    "channel": CHANNELS.WEATHER,
                    "unit": UNITS.RELATIVE_HUMIDITY,
                },
            },
        )

        self.full = Spec(
            datetime_column=self.datetime_column,
            null_check_columns=[
                self.datetime.null_check_columns
                + self.thermostat.null_check_columns
                + self.equipment.null_check_columns
                + self.sensors.null_check_columns
                + self.weather.null_check_columns
            ],
            spec={
                **self.datetime.spec,
                **self.thermostat.spec,
                **self.equipment.spec,
                **self.sensors.spec,
                **self.weather.spec,
            },
        )

    def __setattr__(self, name, value):
        if hasattr(self, name):
            raise AttributeError("Cannot change specification dynamically.")
        else:
            self.__dict__[name] = value

    def get_empty_df(self):
        return pd.DataFrame([], columns=self.full.columns)


class DonateYourDataSpec:
    datetime_format = "utc"
    datetime_column = "DateTime"
    N_ROOM_SENSORS = 10
    data_period_seconds = 300

    def __init__(self):
        self.datetime = Spec(
            datetime_column=self.datetime_column,
            null_check_columns=self.datetime_column,
            spec={
                self.datetime_column: {
                    "internal_state": STATES.DATE_TIME,
                    "dtype": "datetime64[ns, utc]",
                    "channel": CHANNELS.DATETIME,
                    "unit": UNITS.DATETIME,
                },
            },
        )

        self.thermostat = Spec(
            datetime_column=self.datetime_column,
            null_check_columns="HvacMode",
            spec={
                "HvacMode": {
                    "internal_state": STATES.HVAC_MODE,
                    "dtype": "category",
                    "channel": CHANNELS.THERMOSTAT_SETTING,
                    "unit": UNITS.OTHER,
                },
                "Event": {
                    "internal_state": STATES.CALENDAR_EVENT,
                    "dtype": "category",
                    "channel": CHANNELS.THERMOSTAT_SETTING,
                    "unit": UNITS.OTHER,
                },
                "Schedule": {
                    "internal_state": STATES.SCHEDULE,
                    "dtype": "category",
                    "channel": CHANNELS.THERMOSTAT_SETTING,
                    "unit": UNITS.OTHER,
                },
                "T_ctrl": {
                    "internal_state": STATES.TEMPERATURE_CTRL,
                    "dtype": "float32",
                    "channel": CHANNELS.THERMOSTAT_SETTING,
                    "unit": UNITS.FARHENHEIT,
                },
                "T_stp_cool": {
                    "internal_state": STATES.TEMPERATURE_STP_COOL,
                    "dtype": "float32",
                    "channel": CHANNELS.THERMOSTAT_SETTING,
                    "unit": UNITS.FARHENHEIT,
                },
                "T_stp_heat": {
                    "internal_state": STATES.TEMPERATURE_STP_HEAT,
                    "dtype": "float32",
                    "channel": CHANNELS.THERMOSTAT_SETTING,
                    "unit": UNITS.FARHENHEIT,
                },
                "HumidityExpectedLow": {
                    "internal_state": STATES.HUMIDITY_EXPECTED_LOW,
                    "dtype": "float32",
                    "channel": CHANNELS.THERMOSTAT_SETTING,
                    "unit": UNITS.RELATIVE_HUMIDITY,
                },
                "HumidityExpectedHigh": {
                    "internal_state": STATES.HUMIDITY_EXPECTED_HIGH,
                    "dtype": "float32",
                    "channel": CHANNELS.THERMOSTAT_SETTING,
                    "unit": UNITS.RELATIVE_HUMIDITY,
                },
            },
        )

        self.equipment = Spec(
            datetime_column=self.datetime_column,
            null_check_columns="HvacMode",
            spec={
                "auxHeat1": {
                    "internal_state": STATES.AUXHEAT1,
                    "dtype": "int16",
                    "channel": CHANNELS.EQUIPMENT,
                    "unit": UNITS.SECONDS,
                },
                "auxHeat2": {
                    "internal_state": STATES.AUXHEAT2,
                    "dtype": "int16",
                    "channel": CHANNELS.EQUIPMENT,
                    "unit": UNITS.SECONDS,
                },
                "auxHeat3": {
                    "internal_state": STATES.AUXHEAT3,
                    "dtype": "int16",
                    "channel": CHANNELS.EQUIPMENT,
                    "unit": UNITS.SECONDS,
                },
                "compCool1": {
                    "internal_state": STATES.COMPCOOL1,
                    "dtype": "int16",
                    "channel": CHANNELS.EQUIPMENT,
                    "unit": UNITS.SECONDS,
                },
                "compCool2": {
                    "internal_state": STATES.COMPCOOL2,
                    "dtype": "int16",
                    "channel": CHANNELS.EQUIPMENT,
                    "unit": UNITS.SECONDS,
                },
                "compHeat1": {
                    "internal_state": STATES.COMPHEAT1,
                    "dtype": "int16",
                    "channel": CHANNELS.EQUIPMENT,
                    "unit": UNITS.SECONDS,
                },
                "compHeat2": {
                    "internal_state": STATES.COMPHEAT2,
                    "dtype": "int16",
                    "channel": CHANNELS.EQUIPMENT,
                    "unit": UNITS.SECONDS,
                },
                "fan": {
                    "internal_state": STATES.FAN,
                    "dtype": "int16",
                    "channel": CHANNELS.EQUIPMENT,
                    "unit": UNITS.SECONDS,
                },
            },
        )

        self.sensors = Spec(
            datetime_column=self.datetime_column,
            null_check_columns="Thermostat_Temperature",
            spec={
                "Thermostat_Temperature": {
                    "internal_state": STATES.THERMOSTAT_TEMPERATURE,
                    "dtype": "float32",
                    "channel": CHANNELS.THERMOSTAT_SENSOR,
                    "unit": UNITS.FARHENHEIT,
                },
                "Humidity": {
                    "internal_state": STATES.THERMOSTAT_HUMIDITY,
                    "dtype": "float32",
                    "channel": CHANNELS.THERMOSTAT_SENSOR,
                    "unit": UNITS.RELATIVE_HUMIDITY,
                },
                "Thermostat_Motion": {
                    "internal_state": STATES.THERMOSTAT_MOTION,
                    "dtype": "boolean",
                    "channel": CHANNELS.THERMOSTAT_SENSOR,
                    "unit": UNITS.OTHER,
                },
                **{
                    "Remote_Sensor_{}_Temperature".format(i): {
                        "internal_state": STATES[f"RS{i}_TEMPERATURE"],
                        "dtype": "float32",
                        "channel": CHANNELS.REMOTE_SENSOR,
                        "unit": UNITS.CELSIUS,
                    }
                    for i in range(1, self.N_ROOM_SENSORS + 1)
                },
                **{
                    "Remote_Sensor_{}_Motion".format(i): {
                        "internal_state": STATES[f"RS{i}_OCCUPANCY"],
                        "dtype": "boolean",
                        "channel": CHANNELS.REMOTE_SENSOR,
                        "unit": UNITS.OTHER,
                    }
                    for i in range(1, self.N_ROOM_SENSORS + 1)
                },
            },
        )

        self.weather = Spec(
            datetime_column=self.datetime_column,
            null_check_columns="Temperature",
            spec={
                "T_out": {
                    "internal_state": STATES.OUTDOOR_TEMPERATURE,
                    "dtype": "float32",
                    "channel": CHANNELS.WEATHER,
                    "unit": UNITS.FARHENHEIT,
                },
                "RH_out": {
                    "internal_state": STATES.OUTDOOR_RELATIVE_HUMIDITY,
                    "dtype": "float32",
                    "channel": CHANNELS.WEATHER,
                    "unit": UNITS.RELATIVE_HUMIDITY,
                },
            },
        )

        self.full = Spec(
            datetime_column=self.datetime_column,
            null_check_columns=[
                self.datetime.null_check_columns
                + self.thermostat.null_check_columns
                + self.equipment.null_check_columns
                + self.sensors.null_check_columns
                + self.weather.null_check_columns
            ],
            spec={
                **self.datetime.spec,
                **self.thermostat.spec,
                **self.equipment.spec,
                **self.sensors.spec,
                **self.weather.spec,
            },
        )

    def __setattr__(self, name, value):
        if hasattr(self, name):
            raise AttributeError("Cannot change specification dynamically.")
        else:
            self.__dict__[name] = value

    def get_empty_df(self):
        return pd.DataFrame([], columns=self.full.columns)


class EnergyPlusWeather:
    datetime_column = "datetime"

    epw_columns = [
        "year",
        "month",
        "day",
        "hour",
        "minute",
        "data_source_unct",
        "temp_air",
        "temp_dew",
        "relative_humidity",
        "atmospheric_pressure",
        "etr",
        "etrn",
        "ghi_infrared",
        "ghi",
        "dni",
        "dhi",
        "global_hor_illum",
        "direct_normal_illum",
        "diffuse_horizontal_illum",
        "zenith_luminance",
        "wind_direction",
        "wind_speed",
        "total_sky_cover",
        "opaque_sky_cover",
        "visibility",
        "ceiling_height",
        "present_weather_observation",
        "present_weather_codes",
        "precipitable_water",
        "aerosol_optical_depth",
        "snow_depth",
        "days_since_last_snowfall",
        "albedo",
        "liquid_precipitation_depth",
        "liquid_precipitation_quantity",
    ]

    epw_meta = [
        "line_name",
        "city",
        "state-prov",
        "country",
        "data_type",
        "WMO_code",
        "latitude",
        "longitude",
        "TZ",
        "altitude",
    ]

    output_rename_dict = {
        datetime_column: datetime_column,
        STATES.OUTDOOR_TEMPERATURE: "temp_air",
        STATES.OUTDOOR_RELATIVE_HUMIDITY: "relative_humidity",
        STATES.DIRECT_NORMAL_IRRADIANCE: "dni",
        STATES.GLOBAL_HORIZONTAL_IRRADIANCE: "ghi",
        STATES.DIFFUSE_HORIZONTAL_IRRADIANCE: "dhi",
    }
