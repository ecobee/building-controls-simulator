import numpy as np
import pandas as pd
from enum import IntEnum

import attr

# from BuildingControlsSimulator.DataClients.DataChannels import *


class Units(IntEnum):
    """Definition of units for preprocessing to internal unit formats."""

    OTHER = 0
    CELSIUS = 1
    FARHENHEIT = 2
    FARHENHEITx10 = 3
    RELATIVE_HUMIDITY = 4
    DATETIME = 60
    SECONDS = 70


class Channels(IntEnum):
    """Definition of component part of input data for preprocessing to 
    internal formats."""

    OTHER = 0
    HVAC = 1
    TEMPERATURE_SENSOR = 2
    HUMIDITY_SENSOR = 3
    OCCUPANCY_SENSOR = 4
    WEATHER = 5
    DATETIME = 6
    ENERGY_COST = 7


@attr.s(kw_only=True)
class Spec:
    spec = attr.ib()
    null_check_column = attr.ib()
    datetime_column = attr.ib()

    @spec.validator
    def dtypes_are_pandas(self, attribute, value):
        supported_dtypes = [
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
        return {k: v["internal_name"] for k, v in self.spec.items()}


@attr.s(frozen=True)
class Internal:
    """Definition of internal data fields and types.
    For details of string dtype aliases see: 
    https://pandas.pydata.org/pandas-docs/stable/user_guide/basics.html#basics-dtypes
    """

    # TODO: remove .name property if unneeded
    N_ROOM_SENSORS = 10
    datetime_column = "date_time"

    # dtype [ns, TZ] is used to represent the known TZ of data
    datetime = Spec(
        datetime_column=datetime_column,
        null_check_column=datetime_column,
        spec={
            datetime_column: {
                "name": datetime_column,
                "dtype": "datetime64[ns, utc]",
                "channel": Channels.DATETIME,
                "unit": Units.DATETIME,
            },
        },
    )
    hvac = Spec(
        datetime_column=datetime_column,
        null_check_column="hvac_mode",
        spec={
            "hvac_mode": {
                "name": "hvac_mode",
                "dtype": "category",
                "channel": Channels.HVAC,
                "unit": Units.OTHER,
            },
            "system_mode": {
                "name": "system_mode",
                "dtype": "category",
                "channel": Channels.HVAC,
                "unit": Units.OTHER,
            },
            "calendar_event": {
                "name": "calendar_event",
                "dtype": "category",
                "channel": Channels.HVAC,
                "unit": Units.OTHER,
            },
            "climate": {
                "name": "climate",
                "dtype": "category",
                "channel": Channels.HVAC,
                "unit": Units.OTHER,
            },
            "temperature_ctrl": {
                "name": "temperature_ctrl",
                "dtype": "Float32",
                "channel": Channels.HVAC,
                "unit": Units.CELSIUS,
            },
            "temperature_stp_cool": {
                "name": "temperature_stp_cool",
                "dtype": "Float32",
                "channel": Channels.HVAC,
                "unit": Units.CELSIUS,
            },
            "temperature_stp_heat": {
                "name": "temperature_stp_heat",
                "dtype": "Float32",
                "channel": Channels.HVAC,
                "unit": Units.CELSIUS,
            },
            "humidity": {
                "name": "humidity",
                "dtype": "Float32",
                "channel": Channels.HVAC,
                "unit": Units.RELATIVE_HUMIDITY,
            },
            "humidity_expected_low": {
                "name": "humidity_expected_low",
                "dtype": "Float32",
                "channel": Channels.HVAC,
                "unit": Units.RELATIVE_HUMIDITY,
            },
            "humidity_expected_high": {
                "name": "humidity_expected_high",
                "dtype": "Float32",
                "channel": Channels.HVAC,
                "unit": Units.RELATIVE_HUMIDITY,
            },
            "auxHeat1": {
                "name": "auxHeat1",
                "dtype": "Int16",
                "channel": Channels.HVAC,
                "unit": Units.SECONDS,
            },
            "auxHeat2": {
                "name": "auxHeat2",
                "dtype": "Int16",
                "channel": Channels.HVAC,
                "unit": Units.SECONDS,
            },
            "auxHeat3": {
                "name": "auxHeat3",
                "dtype": "Int16",
                "channel": Channels.HVAC,
                "unit": Units.SECONDS,
            },
            "compCool1": {
                "name": "compCool1",
                "dtype": "Int16",
                "channel": Channels.HVAC,
                "unit": Units.SECONDS,
            },
            "compCool2": {
                "name": "compCool2",
                "dtype": "Int16",
                "channel": Channels.HVAC,
                "unit": Units.SECONDS,
            },
            "compHeat1": {
                "name": "compHeat1",
                "dtype": "Int16",
                "channel": Channels.HVAC,
                "unit": Units.SECONDS,
            },
            "compHeat2": {
                "name": "compHeat2",
                "dtype": "Int16",
                "channel": Channels.HVAC,
                "unit": Units.SECONDS,
            },
            "dehumidifier": {
                "name": "dehumidifier",
                "dtype": "Int16",
                "channel": Channels.HVAC,
                "unit": Units.SECONDS,
            },
            "economizer": {
                "name": "economizer",
                "dtype": "Int16",
                "channel": Channels.HVAC,
                "unit": Units.SECONDS,
            },
            "fan": {
                "name": "fan",
                "dtype": "Int16",
                "channel": Channels.HVAC,
                "unit": Units.SECONDS,
            },
            "humidifier": {
                "name": "humidifier",
                "dtype": "Int16",
                "channel": Channels.HVAC,
                "unit": Units.SECONDS,
            },
            "ventilator": {
                "name": "ventilator",
                "dtype": "Int16",
                "channel": Channels.HVAC,
                "unit": Units.SECONDS,
            },
        },
    )

    sensors = Spec(
        datetime_column=datetime_column,
        null_check_column="thermostat_temperature",
        spec={
            "thermostat_temperature": {
                "name": "thermostat_temperature",
                "dtype": "Float32",
                "channel": Channels.TEMPERATURE_SENSOR,
                "unit": Units.CELSIUS,
            },
            "thermostat_humidity": {
                "name": "thermostat_humidity",
                "dtype": "Float32",
                "channel": Channels.HUMIDITY_SENSOR,
                "unit": Units.RELATIVE_HUMIDITY,
            },
            "thermostat_motion": {
                "name": "thermostat_motion",
                "dtype": "boolean",
                "channel": Channels.OCCUPANCY_SENSOR,
                "unit": Units.OTHER,
            },
            **{
                "rs{}_temperature".format(i): {
                    "name": "rs{}_temperature".format(i),
                    "dtype": "Float32",
                    "channel": Channels.TEMPERATURE_SENSOR,
                    "unit": Units.CELSIUS,
                }
                for i in range(1, N_ROOM_SENSORS)
            },
            **{
                "rs{}_occupancy".format(i): {
                    "name": "rs{}_occupancy".format(i),
                    "dtype": "boolean",
                    "channel": Channels.OCCUPANCY_SENSOR,
                    "unit": Units.OTHER,
                }
                for i in range(1, N_ROOM_SENSORS)
            },
        },
    )

    weather = Spec(
        datetime_column=datetime_column,
        null_check_column="outdoor_temperature",
        spec={
            "outdoor_temperature": {
                "name": "outdoor_temperature",
                "dtype": "Float32",
                "channel": Channels.WEATHER,
                "unit": Units.CELSIUS,
            },
            "outdoor_relative_humidity": {
                "name": "outdoor_relative_humidity",
                "dtype": "Float32",
                "channel": Channels.WEATHER,
                "unit": Units.RELATIVE_HUMIDITY,
            },
        },
    )

    full = Spec(
        datetime_column=datetime_column,
        null_check_column=[
            datetime.null_check_column
            + hvac.null_check_column
            + sensors.null_check_column
            + weather.null_check_column
        ],
        spec={**datetime.spec, **hvac.spec, **sensors.spec, **weather.spec,},
    )

    @staticmethod
    def intersect_columns(_df_columns, _spec):
        return [c for c in _df_columns if c in _spec.keys()]

    @staticmethod
    def convert_units_to_internal(df, _spec):
        """This method must be able to evaluate multiple sources should
        a channel be composed from multiple sources."""
        for k, v in _spec.items():
            if v["unit"] != Internal.full.spec[v["internal_name"]]["unit"]:
                if (v["unit"] == Units.FARHENHEIT) and (
                    Internal.full.spec[v["internal_name"]]["unit"]
                    == Units.CELSIUS
                ):
                    df[k] = Internal.F2C(df[k])
                elif (v["unit"] == Units.FARHENHEITx10) and (
                    Internal.full.spec[v["internal_name"]]["unit"]
                    == Units.CELSIUS
                ):
                    df[k] = Internal.F2C(df[k] / 10.0)
                else:
                    logger.error(
                        "Unsupported conversion: {} to {}".format(
                            v["unit"],
                            Internal.full.spec[v["internal_name"]]["unit"],
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
    def F2C(temp_F):
        return (temp_F - 32) * 5 / 9

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
        null_check_column=datetime_column,
        spec={
            datetime_column: {
                "internal_name": "date_time",
                "dtype": "datetime64[ns, utc]",
                "channel": Channels.DATETIME,
                "unit": Units.DATETIME,
            },
        },
    )
    hvac = Spec(
        datetime_column=datetime_column,
        null_check_column="HvacMode",
        spec={
            "HvacMode": {
                "internal_name": "hvac_mode",
                "dtype": "category",
                "channel": Channels.HVAC,
                "unit": Units.OTHER,
            },
            "SystemMode": {
                "internal_name": "system_mode",
                "dtype": "category",
                "channel": Channels.HVAC,
                "unit": Units.OTHER,
            },
            "CalendarEvent": {
                "internal_name": "calendar_event",
                "dtype": "category",
                "channel": Channels.HVAC,
                "unit": Units.OTHER,
            },
            "Climate": {
                "internal_name": "climate",
                "dtype": "category",
                "channel": Channels.HVAC,
                "unit": Units.OTHER,
            },
            "Temperature_ctrl": {
                "internal_name": "temperature_ctrl",
                "dtype": "Int16",
                "channel": Channels.HVAC,
                "unit": Units.FARHENHEITx10,
            },
            "TemperatureExpectedCool": {
                "internal_name": "temperature_stp_cool",
                "dtype": "Int16",
                "channel": Channels.HVAC,
                "unit": Units.FARHENHEITx10,
            },
            "TemperatureExpectedHeat": {
                "internal_name": "temperature_stp_heat",
                "dtype": "Int16",
                "channel": Channels.HVAC,
                "unit": Units.FARHENHEITx10,
            },
            "Humidity": {
                "internal_name": "humidity",
                "dtype": "Float32",
                "channel": Channels.HVAC,
                "unit": Units.RELATIVE_HUMIDITY,
            },
            "HumidityExpectedLow": {
                "internal_name": "humidity_expected_low",
                "dtype": "Float32",
                "channel": Channels.HVAC,
                "unit": Units.RELATIVE_HUMIDITY,
            },
            "HumidityExpectedHigh": {
                "internal_name": "humidity_expected_high",
                "dtype": "Float32",
                "channel": Channels.HVAC,
                "unit": Units.RELATIVE_HUMIDITY,
            },
            "auxHeat1": {
                "internal_name": "auxHeat1",
                "dtype": "Int16",
                "channel": Channels.HVAC,
                "unit": Units.SECONDS,
            },
            "auxHeat2": {
                "internal_name": "auxHeat2",
                "dtype": "Int16",
                "channel": Channels.HVAC,
                "unit": Units.SECONDS,
            },
            "auxHeat3": {
                "internal_name": "auxHeat3",
                "dtype": "Int16",
                "channel": Channels.HVAC,
                "unit": Units.SECONDS,
            },
            "compCool1": {
                "internal_name": "compCool1",
                "dtype": "Int16",
                "channel": Channels.HVAC,
                "unit": Units.SECONDS,
            },
            "compCool2": {
                "internal_name": "compCool2",
                "dtype": "Int16",
                "channel": Channels.HVAC,
                "unit": Units.SECONDS,
            },
            "compHeat1": {
                "internal_name": "compHeat1",
                "dtype": "Int16",
                "channel": Channels.HVAC,
                "unit": Units.SECONDS,
            },
            "compHeat2": {
                "internal_name": "compHeat2",
                "dtype": "Int16",
                "channel": Channels.HVAC,
                "unit": Units.SECONDS,
            },
            "dehumidifier": {
                "internal_name": "dehumidifier",
                "dtype": "Int16",
                "channel": Channels.HVAC,
                "unit": Units.SECONDS,
            },
            "economizer": {
                "internal_name": "economizer",
                "dtype": "Int16",
                "channel": Channels.HVAC,
                "unit": Units.SECONDS,
            },
            "fan": {
                "internal_name": "fan",
                "dtype": "Int16",
                "channel": Channels.HVAC,
                "unit": Units.SECONDS,
            },
            "humidifier": {
                "internal_name": "humidifier",
                "dtype": "Int16",
                "channel": Channels.HVAC,
                "unit": Units.SECONDS,
            },
            "ventilator": {
                "internal_name": "ventilator",
                "dtype": "Int16",
                "channel": Channels.HVAC,
                "unit": Units.SECONDS,
            },
        },
    )

    sensors = Spec(
        datetime_column=datetime_column,
        null_check_column="thermostat_temperature",
        spec={
            "SensorTemp000": {
                "internal_name": "thermostat_temperature",
                "dtype": "Int16",
                "channel": Channels.TEMPERATURE_SENSOR,
                "unit": Units.FARHENHEITx10,
            },
            "SensorHum000": {
                "internal_name": "thermostat_humidity",
                "dtype": "Int16",
                "channel": Channels.HUMIDITY_SENSOR,
                "unit": Units.RELATIVE_HUMIDITY,
            },
            "SensorOcc000": {
                "internal_name": "thermostat_motion",
                "dtype": "boolean",
                "channel": Channels.OCCUPANCY_SENSOR,
                "unit": Units.OTHER,
            },
            **{
                "SensorTemp1{}".format(str(i).zfill(2)): {
                    "internal_name": "rs{}_temperature".format(i),
                    "dtype": "Int16",
                    "channel": Channels.TEMPERATURE_SENSOR,
                    "unit": Units.FARHENHEITx10,
                }
                for i in range(1, N_ROOM_SENSORS)
            },
            **{
                "SensorOcc1{}".format(str(i).zfill(2)): {
                    "internal_name": "rs{}_occupancy".format(i),
                    "dtype": "boolean",
                    "channel": Channels.OCCUPANCY_SENSOR,
                    "unit": Units.OTHER,
                }
                for i in range(1, N_ROOM_SENSORS)
            },
        },
    )

    weather = Spec(
        datetime_column=datetime_column,
        null_check_column="Temperature",
        spec={
            "Temperature": {
                "internal_name": "outdoor_temperature",
                "dtype": "Int16",
                "channel": Channels.WEATHER,
                "unit": Units.FARHENHEITx10,
            },
            "RelativeHumidity": {
                "internal_name": "outdoor_relative_humidity",
                "dtype": "Float32",
                "channel": Channels.WEATHER,
                "unit": Units.RELATIVE_HUMIDITY,
            },
        },
    )

    full = Spec(
        datetime_column=datetime_column,
        null_check_column=[
            datetime.null_check_column
            + hvac.null_check_column
            + sensors.null_check_column
            + weather.null_check_column
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
        null_check_column=datetime_column,
        spec={
            datetime_column: {
                "internal_name": "date_time",
                "dtype": "datetime64[ns, utc]",
                "channel": Channels.DATETIME,
                "unit": Units.DATETIME,
            },
        },
    )
    hvac = Spec(
        datetime_column=datetime_column,
        null_check_column="HvacMode",
        spec={
            "HvacMode": {
                "internal_name": "hvac_mode",
                "dtype": "category",
                "channel": Channels.HVAC,
                "unit": Units.OTHER,
            },
            "Event": {
                "internal_name": "calendar_event",
                "dtype": "category",
                "channel": Channels.HVAC,
                "unit": Units.OTHER,
            },
            "Schedule": {
                "internal_name": "climate",
                "dtype": "category",
                "channel": Channels.HVAC,
                "unit": Units.OTHER,
            },
            "T_ctrl": {
                "internal_name": "temperature_ctrl",
                "dtype": "Int16",
                "channel": Channels.HVAC,
                "unit": Units.FARHENHEIT,
            },
            "T_stp_cool": {
                "internal_name": "temperature_stp_cool",
                "dtype": "Int16",
                "channel": Channels.HVAC,
                "unit": Units.FARHENHEIT,
            },
            "T_stp_heat": {
                "internal_name": "temperature_stp_heat",
                "dtype": "Int16",
                "channel": Channels.HVAC,
                "unit": Units.FARHENHEIT,
            },
            "Humidity": {
                "internal_name": "humidity",
                "dtype": "Float32",
                "channel": Channels.HVAC,
                "unit": Units.RELATIVE_HUMIDITY,
            },
            "HumidityExpectedLow": {
                "internal_name": "humidity_expected_low",
                "dtype": "Float32",
                "channel": Channels.HVAC,
                "unit": Units.RELATIVE_HUMIDITY,
            },
            "HumidityExpectedHigh": {
                "internal_name": "humidity_expected_high",
                "dtype": "Float32",
                "channel": Channels.HVAC,
                "unit": Units.RELATIVE_HUMIDITY,
            },
            "auxHeat1": {
                "internal_name": "auxHeat1",
                "dtype": "Int16",
                "channel": Channels.HVAC,
                "unit": Units.SECONDS,
            },
            "auxHeat2": {
                "internal_name": "auxHeat2",
                "dtype": "Int16",
                "channel": Channels.HVAC,
                "unit": Units.SECONDS,
            },
            "auxHeat3": {
                "internal_name": "auxHeat3",
                "dtype": "Int16",
                "channel": Channels.HVAC,
                "unit": Units.SECONDS,
            },
            "compCool1": {
                "internal_name": "compCool1",
                "dtype": "Int16",
                "channel": Channels.HVAC,
                "unit": Units.SECONDS,
            },
            "compCool2": {
                "internal_name": "compCool2",
                "dtype": "Int16",
                "channel": Channels.HVAC,
                "unit": Units.SECONDS,
            },
            "compHeat1": {
                "internal_name": "compHeat1",
                "dtype": "Int16",
                "channel": Channels.HVAC,
                "unit": Units.SECONDS,
            },
            "compHeat2": {
                "internal_name": "compHeat2",
                "dtype": "Int16",
                "channel": Channels.HVAC,
                "unit": Units.SECONDS,
            },
            "fan": {
                "internal_name": "fan",
                "dtype": "Int16",
                "channel": Channels.HVAC,
                "unit": Units.SECONDS,
            },
        },
    )

    sensors = Spec(
        datetime_column=datetime_column,
        null_check_column="Thermostat_Temperature",
        spec={
            "Thermostat_Temperature": {
                "internal_name": "thermostat_temperature",
                "dtype": "Int16",
                "channel": Channels.TEMPERATURE_SENSOR,
                "unit": Units.FARHENHEIT,
            },
            "Humidity": {
                "internal_name": "thermostat_humidity",
                "dtype": "Int16",
                "channel": Channels.HUMIDITY_SENSOR,
                "unit": Units.RELATIVE_HUMIDITY,
            },
            "Thermostat_Motion": {
                "internal_name": "thermostat_motion",
                "dtype": "boolean",
                "channel": Channels.OCCUPANCY_SENSOR,
                "unit": Units.OTHER,
            },
            **{
                "Remote_Sensor_{}_Temperature".format(i): {
                    "internal_name": "rs{}_temperature".format(i),
                    "dtype": "Int16",
                    "channel": Channels.TEMPERATURE_SENSOR,
                    "unit": Units.CELSIUS,
                }
                for i in range(1, N_ROOM_SENSORS)
            },
            **{
                "Remote_Sensor_{}_Motion".format(i): {
                    "internal_name": "rs{}_occupancy".format(i),
                    "dtype": "boolean",
                    "channel": Channels.OCCUPANCY_SENSOR,
                    "unit": Units.OTHER,
                }
                for i in range(1, N_ROOM_SENSORS)
            },
        },
    )

    weather = Spec(
        datetime_column=datetime_column,
        null_check_column="Temperature",
        spec={
            "T_out": {
                "internal_name": "outdoor_temperature",
                "dtype": "Int16",
                "channel": Channels.WEATHER,
                "unit": Units.FARHENHEIT,
            },
            "RH_out": {
                "internal_name": "outdoor_relative_humidity",
                "dtype": "Float32",
                "channel": Channels.WEATHER,
                "unit": Units.RELATIVE_HUMIDITY,
            },
        },
    )

    full = Spec(
        datetime_column=datetime_column,
        null_check_column=[
            datetime.null_check_column
            + hvac.null_check_column
            + sensors.null_check_column
            + weather.null_check_column
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
        "outdoor_temperature": "temp_air",
        "outdoor_relative_humidity": "relative_humidity",
    }

