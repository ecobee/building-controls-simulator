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


@attr.s(kw_only=True)
class Spec:
    spec = attr.ib()
    null_check_columns = attr.ib()
    datetime_column = attr.ib()

    @spec.validator
    def dtypes_are_pandas(self, attribute, value):
        supported_dtypes = [
            "bool",
            "string",
            "Float32",
            "float32",
            "Float64",
            "float64",
            "Int8",
            "Int16",
            "Int32",
            "Int64",
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

    def get_dtype_mapper(self, _df_columns):
        return {
            k: v["dtype"] for k, v in self.spec.items() if k in _df_columns
        }

    def get_rename_mapper(self):
        return {k: v["internal_state"] for k, v in self.spec.items()}


@attr.s(frozen=True)
class Internal:
    """Definition of internal data fields and types.
    For details of string dtype aliases see: 
    https://pandas.pydata.org/pandas-docs/stable/user_guide/basics.html#basics-dtypes
    """

    # TODO: remove .name property if unneeded
    N_ROOM_SENSORS = 10
    datetime_column = STATES.DATE_TIME

    # dtype [ns, TZ] is used to represent the known TZ of data
    # do not need Enum value for only one column
    datetime = Spec(
        datetime_column=datetime_column,
        null_check_columns=[datetime_column],
        spec={
            datetime_column: {
                "name": "date_time",
                "dtype": "datetime64[ns, utc]",
                "channel": CHANNELS.DATETIME,
                "unit": UNITS.DATETIME,
            },
        },
    )
    hvac = Spec(
        datetime_column=datetime_column,
        null_check_columns=[STATES.HVAC_MODE],
        spec={
            STATES.HVAC_MODE: {
                "name": "hvac_mode",
                "dtype": "category",
                "channel": CHANNELS.HVAC,
                "unit": UNITS.OTHER,
            },
            STATES.SYSTEM_MODE: {
                "name": "system_mode",
                "dtype": "category",
                "channel": CHANNELS.HVAC,
                "unit": UNITS.OTHER,
            },
            STATES.CALENDAR_EVENT: {
                "name": "calendar_event",
                "dtype": "category",
                "channel": CHANNELS.HVAC,
                "unit": UNITS.OTHER,
            },
            STATES.SCHEDULE: {
                "name": "schedule",
                "dtype": "category",
                "channel": CHANNELS.HVAC,
                "unit": UNITS.OTHER,
            },
            STATES.TEMPERATURE_CTRL: {
                "name": "temperature_ctrl",
                "dtype": "Float32",
                "channel": CHANNELS.HVAC,
                "unit": UNITS.CELSIUS,
            },
            STATES.TEMPERATURE_STP_COOL: {
                "name": "temperature_stp_cool",
                "dtype": "Float32",
                "channel": CHANNELS.HVAC,
                "unit": UNITS.CELSIUS,
            },
            STATES.TEMPERATURE_STP_HEAT: {
                "name": "temperature_stp_heat",
                "dtype": "Float32",
                "channel": CHANNELS.HVAC,
                "unit": UNITS.CELSIUS,
            },
            STATES.HUMIDITY: {
                "name": "humidity",
                "dtype": "Float32",
                "channel": CHANNELS.HVAC,
                "unit": UNITS.RELATIVE_HUMIDITY,
            },
            STATES.HUMIDITY_EXPECTED_LOW: {
                "name": "humidity_expected_low",
                "dtype": "Float32",
                "channel": CHANNELS.HVAC,
                "unit": UNITS.RELATIVE_HUMIDITY,
            },
            STATES.HUMIDITY_EXPECTED_HIGH: {
                "name": "humidity_expected_high",
                "dtype": "Float32",
                "channel": CHANNELS.HVAC,
                "unit": UNITS.RELATIVE_HUMIDITY,
            },
            STATES.AUXHEAT1: {
                "name": "auxHeat1",
                "dtype": "Int16",
                "channel": CHANNELS.HVAC,
                "unit": UNITS.SECONDS,
            },
            STATES.AUXHEAT2: {
                "name": "auxHeat2",
                "dtype": "Int16",
                "channel": CHANNELS.HVAC,
                "unit": UNITS.SECONDS,
            },
            STATES.AUXHEAT3: {
                "name": "auxHeat3",
                "dtype": "Int16",
                "channel": CHANNELS.HVAC,
                "unit": UNITS.SECONDS,
            },
            STATES.COMPCOOL1: {
                "name": "compCool1",
                "dtype": "Int16",
                "channel": CHANNELS.HVAC,
                "unit": UNITS.SECONDS,
            },
            STATES.COMPCOOL2: {
                "name": "compCool2",
                "dtype": "Int16",
                "channel": CHANNELS.HVAC,
                "unit": UNITS.SECONDS,
            },
            STATES.COMPHEAT1: {
                "name": "compHeat1",
                "dtype": "Int16",
                "channel": CHANNELS.HVAC,
                "unit": UNITS.SECONDS,
            },
            STATES.COMPHEAT2: {
                "name": "compHeat2",
                "dtype": "Int16",
                "channel": CHANNELS.HVAC,
                "unit": UNITS.SECONDS,
            },
            STATES.DEHUMIDIFIER: {
                "name": "dehumidifier",
                "dtype": "Int16",
                "channel": CHANNELS.HVAC,
                "unit": UNITS.SECONDS,
            },
            STATES.ECONOMIZER: {
                "name": "economizer",
                "dtype": "Int16",
                "channel": CHANNELS.HVAC,
                "unit": UNITS.SECONDS,
            },
            STATES.FAN: {
                "name": "fan",
                "dtype": "Int16",
                "channel": CHANNELS.HVAC,
                "unit": UNITS.SECONDS,
            },
            STATES.FAN_STAGE_ONE: {
                "name": "fan",
                "dtype": "Int16",
                "channel": CHANNELS.HVAC,
                "unit": UNITS.SECONDS,
            },
            STATES.FAN_STAGE_TWO: {
                "name": "fan",
                "dtype": "Int16",
                "channel": CHANNELS.HVAC,
                "unit": UNITS.SECONDS,
            },
            STATES.FAN_STAGE_THREE: {
                "name": "fan",
                "dtype": "Int16",
                "channel": CHANNELS.HVAC,
                "unit": UNITS.SECONDS,
            },
            STATES.HUMIDIFIER: {
                "name": "humidifier",
                "dtype": "Int16",
                "channel": CHANNELS.HVAC,
                "unit": UNITS.SECONDS,
            },
            STATES.VENTILATOR: {
                "name": "ventilator",
                "dtype": "Int16",
                "channel": CHANNELS.HVAC,
                "unit": UNITS.SECONDS,
            },
        },
    )

    sensors = Spec(
        datetime_column=datetime_column,
        null_check_columns=[STATES.THERMOSTAT_TEMPERATURE],
        spec={
            STATES.THERMOSTAT_TEMPERATURE: {
                "name": "thermostat_temperature",
                "dtype": "Float32",
                "channel": CHANNELS.TEMPERATURE_SENSOR,
                "unit": UNITS.CELSIUS,
            },
            STATES.THERMOSTAT_HUMIDITY: {
                "name": "thermostat_humidity",
                "dtype": "Float32",
                "channel": CHANNELS.HUMIDITY_SENSOR,
                "unit": UNITS.RELATIVE_HUMIDITY,
            },
            STATES.THERMOSTAT_MOTION: {
                "name": "thermostat_motion",
                "dtype": "bool",
                "channel": CHANNELS.OCCUPANCY_SENSOR,
                "unit": UNITS.OTHER,
            },
            **{
                STATES["RS{}_TEMPERATURE".format(i)]: {
                    "name": "rs{}_temperature".format(i),
                    "dtype": "Float32",
                    "channel": CHANNELS.TEMPERATURE_SENSOR,
                    "unit": UNITS.CELSIUS,
                }
                for i in range(1, N_ROOM_SENSORS)
            },
            **{
                STATES["RS{}_OCCUPANCY".format(i)]: {
                    "name": "rs{}_occupancy".format(i),
                    "dtype": "bool",
                    "channel": CHANNELS.OCCUPANCY_SENSOR,
                    "unit": UNITS.OTHER,
                }
                for i in range(1, N_ROOM_SENSORS)
            },
        },
    )

    weather = Spec(
        datetime_column=datetime_column,
        null_check_columns=[STATES.OUTDOOR_TEMPERATURE],
        spec={
            STATES.OUTDOOR_TEMPERATURE: {
                "name": "outdoor_temperature",
                "dtype": "Float32",
                "channel": CHANNELS.WEATHER,
                "unit": UNITS.CELSIUS,
            },
            STATES.OUTDOOR_RELATIVE_HUMIDITY: {
                "name": "outdoor_relative_humidity",
                "dtype": "Float32",
                "channel": CHANNELS.WEATHER,
                "unit": UNITS.RELATIVE_HUMIDITY,
            },
        },
    )

    simulation = Spec(
        datetime_column=datetime_column,
        null_check_columns="Temperature",
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

    full = Spec(
        datetime_column=datetime_column,
        null_check_columns=[
            datetime.null_check_columns
            + hvac.null_check_columns
            + sensors.null_check_columns
            + weather.null_check_columns
        ],
        spec={
            **datetime.spec,
            **hvac.spec,
            **sensors.spec,
            **weather.spec,
            **simulation.spec,
        },
    )

    @staticmethod
    def intersect_columns(_df_columns, _spec):
        return [c for c in _df_columns if c in _spec.keys()]

    @staticmethod
    def convert_units_to_internal(df, _spec):
        """This method must be able to evaluate multiple sources should
        a channel be composed from multiple sources."""
        for k, v in _spec.items():
            if v["unit"] != Internal.full.spec[v["internal_state"]]["unit"]:
                if (v["unit"] == UNITS.FARHENHEIT) and (
                    Internal.full.spec[v["internal_state"]]["unit"]
                    == UNITS.CELSIUS
                ):
                    df[k] = Conversions.F2C(df[k])
                elif (v["unit"] == UNITS.FARHENHEITx10) and (
                    Internal.full.spec[v["internal_state"]]["unit"]
                    == UNITS.CELSIUS
                ):
                    df[k] = Conversions.F2C(df[k] / 10.0)
                else:
                    logger.error(
                        "Unsupported conversion: {} to {}".format(
                            v["unit"],
                            Internal.full.spec[v["internal_state"]]["unit"],
                        )
                    )
        return df

    @staticmethod
    def convert_to_internal(_df, _spec):
        _df = Internal.convert_units_to_internal(_df, _spec.spec)
        _df = _df.rename(columns=_spec.get_rename_mapper())
        _df = _df.astype(dtype=Internal.full.get_dtype_mapper(_df.columns))
        _df = _df.sort_values(Internal.datetime_column, ascending=True)
        return _df

    @staticmethod
    def get_empty_df():
        return pd.DataFrame([], columns=Internal.full.columns)


@attr.s()
class FlatFilesSpec:
    datetime_format = "utc"
    datetime_column = "date_time"
    N_ROOM_SENSORS = 10
    datetime = Spec(
        datetime_column=datetime_column,
        null_check_columns=datetime_column,
        spec={
            datetime_column: {
                "internal_state": STATES.DATE_TIME,
                "dtype": "datetime64[ns, utc]",
                "channel": CHANNELS.DATETIME,
                "unit": UNITS.DATETIME,
            },
        },
    )
    hvac = Spec(
        datetime_column=datetime_column,
        null_check_columns="HvacMode",
        spec={
            "HvacMode": {
                "internal_state": STATES.HVAC_MODE,
                "dtype": "category",
                "channel": CHANNELS.HVAC,
                "unit": UNITS.OTHER,
            },
            "SystemMode": {
                "internal_state": STATES.SYSTEM_MODE,
                "dtype": "category",
                "channel": CHANNELS.HVAC,
                "unit": UNITS.OTHER,
            },
            "CalendarEvent": {
                "internal_state": STATES.CALENDAR_EVENT,
                "dtype": "category",
                "channel": CHANNELS.HVAC,
                "unit": UNITS.OTHER,
            },
            "Climate": {
                "internal_state": STATES.SCHEDULE,
                "dtype": "category",
                "channel": CHANNELS.HVAC,
                "unit": UNITS.OTHER,
            },
            "Temperature_ctrl": {
                "internal_state": STATES.TEMPERATURE_CTRL,
                "dtype": "Int16",
                "channel": CHANNELS.HVAC,
                "unit": UNITS.FARHENHEITx10,
            },
            "TemperatureExpectedCool": {
                "internal_state": STATES.TEMPERATURE_STP_COOL,
                "dtype": "Int16",
                "channel": CHANNELS.HVAC,
                "unit": UNITS.FARHENHEITx10,
            },
            "TemperatureExpectedHeat": {
                "internal_state": STATES.TEMPERATURE_STP_HEAT,
                "dtype": "Int16",
                "channel": CHANNELS.HVAC,
                "unit": UNITS.FARHENHEITx10,
            },
            "Humidity": {
                "internal_state": STATES.HUMIDITY,
                "dtype": "Float32",
                "channel": CHANNELS.HVAC,
                "unit": UNITS.RELATIVE_HUMIDITY,
            },
            "HumidityExpectedLow": {
                "internal_state": STATES.HUMIDITY_EXPECTED_LOW,
                "dtype": "Float32",
                "channel": CHANNELS.HVAC,
                "unit": UNITS.RELATIVE_HUMIDITY,
            },
            "HumidityExpectedHigh": {
                "internal_state": STATES.HUMIDITY_EXPECTED_HIGH,
                "dtype": "Float32",
                "channel": CHANNELS.HVAC,
                "unit": UNITS.RELATIVE_HUMIDITY,
            },
            "auxHeat1": {
                "internal_state": STATES.AUXHEAT1,
                "dtype": "Int16",
                "channel": CHANNELS.HVAC,
                "unit": UNITS.SECONDS,
            },
            "auxHeat2": {
                "internal_state": STATES.AUXHEAT2,
                "dtype": "Int16",
                "channel": CHANNELS.HVAC,
                "unit": UNITS.SECONDS,
            },
            "auxHeat3": {
                "internal_state": STATES.AUXHEAT3,
                "dtype": "Int16",
                "channel": CHANNELS.HVAC,
                "unit": UNITS.SECONDS,
            },
            "compCool1": {
                "internal_state": STATES.COMPCOOL1,
                "dtype": "Int16",
                "channel": CHANNELS.HVAC,
                "unit": UNITS.SECONDS,
            },
            "compCool2": {
                "internal_state": STATES.COMPCOOL2,
                "dtype": "Int16",
                "channel": CHANNELS.HVAC,
                "unit": UNITS.SECONDS,
            },
            "compHeat1": {
                "internal_state": STATES.COMPHEAT1,
                "dtype": "Int16",
                "channel": CHANNELS.HVAC,
                "unit": UNITS.SECONDS,
            },
            "compHeat2": {
                "internal_state": STATES.COMPHEAT2,
                "dtype": "Int16",
                "channel": CHANNELS.HVAC,
                "unit": UNITS.SECONDS,
            },
            "dehumidifier": {
                "internal_state": STATES.DEHUMIDIFIER,
                "dtype": "Int16",
                "channel": CHANNELS.HVAC,
                "unit": UNITS.SECONDS,
            },
            "economizer": {
                "internal_state": STATES.ECONOMIZER,
                "dtype": "Int16",
                "channel": CHANNELS.HVAC,
                "unit": UNITS.SECONDS,
            },
            "fan": {
                "internal_state": STATES.FAN,
                "dtype": "Int16",
                "channel": CHANNELS.HVAC,
                "unit": UNITS.SECONDS,
            },
            "humidifier": {
                "internal_state": STATES.HUMIDIFIER,
                "dtype": "Int16",
                "channel": CHANNELS.HVAC,
                "unit": UNITS.SECONDS,
            },
            "ventilator": {
                "internal_state": STATES.VENTILATOR,
                "dtype": "Int16",
                "channel": CHANNELS.HVAC,
                "unit": UNITS.SECONDS,
            },
        },
    )

    sensors = Spec(
        datetime_column=datetime_column,
        null_check_columns="thermostat_temperature",
        spec={
            "SensorTemp000": {
                "internal_state": STATES.THERMOSTAT_TEMPERATURE,
                "dtype": "Int16",
                "channel": CHANNELS.TEMPERATURE_SENSOR,
                "unit": UNITS.FARHENHEITx10,
            },
            "SensorHum000": {
                "internal_state": STATES.THERMOSTAT_HUMIDITY,
                "dtype": "Int16",
                "channel": CHANNELS.HUMIDITY_SENSOR,
                "unit": UNITS.RELATIVE_HUMIDITY,
            },
            "SensorOcc000": {
                "internal_state": STATES.THERMOSTAT_MOTION,
                "dtype": "bool",
                "channel": CHANNELS.OCCUPANCY_SENSOR,
                "unit": UNITS.OTHER,
            },
            **{
                "SensorTemp1{}".format(str(i).zfill(2)): {
                    "internal_state": STATES["RS{}_TEMPERATURE".format(i)],
                    "dtype": "Int16",
                    "channel": CHANNELS.TEMPERATURE_SENSOR,
                    "unit": UNITS.FARHENHEITx10,
                }
                for i in range(1, N_ROOM_SENSORS)
            },
            **{
                "SensorOcc1{}".format(str(i).zfill(2)): {
                    "internal_state": STATES["RS{}_OCCUPANCY".format(i)],
                    "dtype": "bool",
                    "channel": CHANNELS.OCCUPANCY_SENSOR,
                    "unit": UNITS.OTHER,
                }
                for i in range(1, N_ROOM_SENSORS)
            },
        },
    )

    weather = Spec(
        datetime_column=datetime_column,
        null_check_columns="Temperature",
        spec={
            "Temperature": {
                "internal_state": STATES.OUTDOOR_TEMPERATURE,
                "dtype": "Int16",
                "channel": CHANNELS.WEATHER,
                "unit": UNITS.FARHENHEITx10,
            },
            "RelativeHumidity": {
                "internal_state": STATES.OUTDOOR_RELATIVE_HUMIDITY,
                "dtype": "Float32",
                "channel": CHANNELS.WEATHER,
                "unit": UNITS.RELATIVE_HUMIDITY,
            },
        },
    )

    full = Spec(
        datetime_column=datetime_column,
        null_check_columns=[
            datetime.null_check_columns
            + hvac.null_check_columns
            + sensors.null_check_columns
            + weather.null_check_columns
        ],
        spec={**datetime.spec, **hvac.spec, **sensors.spec, **weather.spec,},
    )


@attr.s()
class DonateYourDataSpec:
    datetime_format = "utc"
    datetime_column = "DateTime"
    N_ROOM_SENSORS = 10
    datetime = Spec(
        datetime_column=datetime_column,
        null_check_columns=datetime_column,
        spec={
            datetime_column: {
                "internal_state": STATES.DATE_TIME,
                "dtype": "datetime64[ns, utc]",
                "channel": CHANNELS.DATETIME,
                "unit": UNITS.DATETIME,
            },
        },
    )
    hvac = Spec(
        datetime_column=datetime_column,
        null_check_columns="HvacMode",
        spec={
            "HvacMode": {
                "internal_state": STATES.HVAC_MODE,
                "dtype": "category",
                "channel": CHANNELS.HVAC,
                "unit": UNITS.OTHER,
            },
            "Event": {
                "internal_state": STATES.CALENDAR_EVENT,
                "dtype": "category",
                "channel": CHANNELS.HVAC,
                "unit": UNITS.OTHER,
            },
            "Schedule": {
                "internal_state": STATES.SCHEDULE,
                "dtype": "category",
                "channel": CHANNELS.HVAC,
                "unit": UNITS.OTHER,
            },
            "T_ctrl": {
                "internal_state": STATES.TEMPERATURE_CTRL,
                "dtype": "Int16",
                "channel": CHANNELS.HVAC,
                "unit": UNITS.FARHENHEIT,
            },
            "T_stp_cool": {
                "internal_state": STATES.TEMPERATURE_STP_COOL,
                "dtype": "Int16",
                "channel": CHANNELS.HVAC,
                "unit": UNITS.FARHENHEIT,
            },
            "T_stp_heat": {
                "internal_state": STATES.TEMPERATURE_STP_HEAT,
                "dtype": "Int16",
                "channel": CHANNELS.HVAC,
                "unit": UNITS.FARHENHEIT,
            },
            "Humidity": {
                "internal_state": STATES.HUMIDITY,
                "dtype": "Float32",
                "channel": CHANNELS.HVAC,
                "unit": UNITS.RELATIVE_HUMIDITY,
            },
            "HumidityExpectedLow": {
                "internal_state": STATES.HUMIDITY_EXPECTED_LOW,
                "dtype": "Float32",
                "channel": CHANNELS.HVAC,
                "unit": UNITS.RELATIVE_HUMIDITY,
            },
            "HumidityExpectedHigh": {
                "internal_state": STATES.HUMIDITY_EXPECTED_HIGH,
                "dtype": "Float32",
                "channel": CHANNELS.HVAC,
                "unit": UNITS.RELATIVE_HUMIDITY,
            },
            "auxHeat1": {
                "internal_state": STATES.AUXHEAT1,
                "dtype": "Int16",
                "channel": CHANNELS.HVAC,
                "unit": UNITS.SECONDS,
            },
            "auxHeat2": {
                "internal_state": STATES.AUXHEAT2,
                "dtype": "Int16",
                "channel": CHANNELS.HVAC,
                "unit": UNITS.SECONDS,
            },
            "auxHeat3": {
                "internal_state": STATES.AUXHEAT3,
                "dtype": "Int16",
                "channel": CHANNELS.HVAC,
                "unit": UNITS.SECONDS,
            },
            "compCool1": {
                "internal_state": STATES.COMPCOOL1,
                "dtype": "Int16",
                "channel": CHANNELS.HVAC,
                "unit": UNITS.SECONDS,
            },
            "compCool2": {
                "internal_state": STATES.COMPCOOL2,
                "dtype": "Int16",
                "channel": CHANNELS.HVAC,
                "unit": UNITS.SECONDS,
            },
            "compHeat1": {
                "internal_state": STATES.COMPHEAT1,
                "dtype": "Int16",
                "channel": CHANNELS.HVAC,
                "unit": UNITS.SECONDS,
            },
            "compHeat2": {
                "internal_state": STATES.COMPHEAT2,
                "dtype": "Int16",
                "channel": CHANNELS.HVAC,
                "unit": UNITS.SECONDS,
            },
            "fan": {
                "internal_state": STATES.FAN,
                "dtype": "Int16",
                "channel": CHANNELS.HVAC,
                "unit": UNITS.SECONDS,
            },
        },
    )

    sensors = Spec(
        datetime_column=datetime_column,
        null_check_columns="Thermostat_Temperature",
        spec={
            "Thermostat_Temperature": {
                "internal_state": STATES.THERMOSTAT_TEMPERATURE,
                "dtype": "Int16",
                "channel": CHANNELS.TEMPERATURE_SENSOR,
                "unit": UNITS.FARHENHEIT,
            },
            "Humidity": {
                "internal_state": STATES.THERMOSTAT_HUMIDITY,
                "dtype": "Int16",
                "channel": CHANNELS.HUMIDITY_SENSOR,
                "unit": UNITS.RELATIVE_HUMIDITY,
            },
            "Thermostat_Motion": {
                "internal_state": STATES.THERMOSTAT_MOTION,
                "dtype": "bool",
                "channel": CHANNELS.OCCUPANCY_SENSOR,
                "unit": UNITS.OTHER,
            },
            **{
                "Remote_Sensor_{}_Temperature".format(i): {
                    "internal_state": STATES[f"RS{i}_TEMPERATURE"],
                    "dtype": "Int16",
                    "channel": CHANNELS.TEMPERATURE_SENSOR,
                    "unit": UNITS.CELSIUS,
                }
                for i in range(1, N_ROOM_SENSORS)
            },
            **{
                "Remote_Sensor_{}_Motion".format(i): {
                    "internal_state": STATES[f"RS{i}_OCCUPANCY"],
                    "dtype": "bool",
                    "channel": CHANNELS.OCCUPANCY_SENSOR,
                    "unit": UNITS.OTHER,
                }
                for i in range(1, N_ROOM_SENSORS)
            },
        },
    )

    weather = Spec(
        datetime_column=datetime_column,
        null_check_columns="Temperature",
        spec={
            "T_out": {
                "internal_state": STATES.OUTDOOR_TEMPERATURE,
                "dtype": "Int16",
                "channel": CHANNELS.WEATHER,
                "unit": UNITS.FARHENHEIT,
            },
            "RH_out": {
                "internal_state": STATES.OUTDOOR_RELATIVE_HUMIDITY,
                "dtype": "Float32",
                "channel": CHANNELS.WEATHER,
                "unit": UNITS.RELATIVE_HUMIDITY,
            },
        },
    )

    full = Spec(
        datetime_column=datetime_column,
        null_check_columns=[
            datetime.null_check_columns
            + hvac.null_check_columns
            + sensors.null_check_columns
            + weather.null_check_columns
        ],
        spec={**datetime.spec, **hvac.spec, **sensors.spec, **weather.spec,},
    )


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
        Internal.datetime_column: datetime_column,
        STATES.OUTDOOR_TEMPERATURE: "temp_air",
        STATES.OUTDOOR_RELATIVE_HUMIDITY: "relative_humidity",
    }

