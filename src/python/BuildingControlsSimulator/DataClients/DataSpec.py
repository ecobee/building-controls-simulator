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

    @property
    def columns(self):
        return list(self.spec.keys())

    def get_dtype_mapper(self):
        return {k: v["dtype"] for k, v in self.spec.items()}

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
    def convert_units_to_internal(df, spec):
        """This method must be able to evaluate multiple sources should
        a channel be composed from multiple sources."""
        for k, v in spec.items():
            if v["unit"] != Internal.full.spec[v["internal_name"]]["unit"]:
                print(
                    "Convert: {} to {}".format(
                        v["unit"],
                        Internal.full.spec[v["internal_name"]]["unit"],
                    )
                )
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
        return df

    @staticmethod
    def convert_to_internal(_df, _spec):
        _df = Internal.convert_units_to_internal(_df, _spec.spec)
        _df = _df.rename(columns=_spec.get_rename_mapper())
        _df = _df.astype(dtype=Internal.full.get_dtype_mapper())
        return _df

    @staticmethod
    def F2C(temp_F):
        return (temp_F - 32) * 5 / 9

    @staticmethod
    def get_empty_df():
        return pd.DataFrame([], columns=Internal.full.columns)


@attr.s(frozen=True)
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


# class CACHE_ISM_COLUMNS:

#     WEATHER = ["Temperature", "RelativeHumidity"]
#     DATETIME = "date_time"

#     OCCUPANCY = [
#         "SensorOcc000",
#         "SensorOcc100",
#         "SensorOcc101",
#         "SensorOcc102",
#         "SensorOcc103",
#         "SensorOcc104",
#         "SensorOcc105",
#         "SensorOcc106",
#         "SensorOcc107",
#         "SensorOcc108",
#         "SensorOcc109",
#         # "SensorOcc110",
#         # "SensorOcc111",
#         # "SensorOcc112",
#         # "SensorOcc113",
#         # "SensorOcc114",
#         # "SensorOcc115",
#         # "SensorOcc116",
#         # "SensorOcc117",
#         # "SensorOcc118",
#         # "SensorOcc119",
#         # "SensorOcc120",
#         # "SensorOcc121",
#         # "SensorOcc122",
#         # "SensorOcc123",
#         # "SensorOcc124",
#         # "SensorOcc125",
#         # "SensorOcc126",
#         # "SensorOcc127",
#         # "SensorOcc128",
#         # "SensorOcc129",
#         # "SensorOcc130",
#         # "SensorOcc131",
#     ]
#     HVAC = [
#         "HvacMode",
#         "SystemMode",
#         "CalendarEvent",
#         "Climate",
#         "Temperature_ctrl",
#         "TemperatureExpectedCool",
#         "TemperatureExpectedHeat",
#         "Humidity",
#         "HumidityExpectedLow",
#         "HumidityExpectedHigh",
#         "auxHeat1",
#         "auxHeat2",
#         "auxHeat3",
#         "compCool1",
#         "compCool2",
#         "compHeat1",
#         "compHeat2",
#         "dehumidifier",
#         "economizer",
#         "fan",
#         "humidifier",
#         "ventilator",
#         "SensorHum000",
#         "SensorTemp000",
#         "SensorTemp100",
#         "SensorTemp101",
#         "SensorTemp102",
#         "SensorTemp103",
#         "SensorTemp104",
#         "SensorTemp105",
#         "SensorTemp106",
#         "SensorTemp107",
#         "SensorTemp108",
#         "SensorTemp109",
#         # "SensorTemp110",
#         # "SensorTemp111",
#         # "SensorTemp112",
#         # "SensorTemp113",
#         # "SensorTemp114",
#         # "SensorTemp115",
#         # "SensorTemp116",
#         # "SensorTemp117",
#         # "SensorTemp118",
#         # "SensorTemp119",
#         # "SensorTemp120",
#         # "SensorTemp121",
#         # "SensorTemp122",
#         # "SensorTemp123",
#         # "SensorTemp124",
#         # "SensorTemp125",
#         # "SensorTemp126",
#         # "SensorTemp127",
#         # "SensorTemp128",
#         # "SensorTemp129",
#         # "SensorTemp130",
#         # "SensorTemp131",
#     ]

#     INTERNAL_MAP = {
#         DATETIME: "datetime",
#         "HvacMode": "HvacMode",
#         "CalendarEvent": "Event",
#         "Climate": "Schedule",
#         "Temperature_ctrl": "T_ctrl",
#         "TemperatureExpectedCool": "T_stp_cool",
#         "TemperatureExpectedHeat": "T_stp_heat",
#         "Humidity": "Thermostat_Humidity",
#         # "HumidityExpectedLow",
#         # "HumidityExpectedHigh",
#         # "auxHeat1",
#         # "auxHeat2",
#         # "auxHeat3",
#         # "compCool1",
#         # "compCool2",
#         # "compHeat1",
#         # "compHeat2",
#         # "dehumidifier",
#         # "economizer",
#         # "fan",
#         # "humidifier",
#         # "ventilator",
#         "SensorTemp000": "Thermostat_Temperature",
#         "SensorHum000": "Thermostat_Humidity",
#         "SensorTemp100": "Remote_Sensor_1_Temperature",
#         "SensorTemp101": "Remote_Sensor_2_Temperature",
#         "SensorTemp102": "Remote_Sensor_3_Temperature",
#         "SensorTemp103": "Remote_Sensor_4_Temperature",
#         "SensorTemp104": "Remote_Sensor_5_Temperature",
#         "SensorTemp105": "Remote_Sensor_6_Temperature",
#         "SensorTemp106": "Remote_Sensor_7_Temperature",
#         "SensorTemp107": "Remote_Sensor_8_Temperature",
#         "SensorTemp108": "Remote_Sensor_9_Temperature",
#         "SensorTemp109": "Remote_Sensor_10_Temperature",
#     }

#     TEMPERATURE = [
#         "T_ctrl",
#         "T_stp_cool",
#         "T_stp_heat",
#         "Thermostat_Temperature",
#         "Remote_Sensor_1_Temperature",
#         "Remote_Sensor_2_Temperature",
#         "Remote_Sensor_3_Temperature",
#         "Remote_Sensor_4_Temperature",
#         "Remote_Sensor_5_Temperature",
#         "Remote_Sensor_6_Temperature",
#         "Remote_Sensor_7_Temperature",
#         "Remote_Sensor_8_Temperature",
#         "Remote_Sensor_9_Temperature",
#         "Remote_Sensor_10_Temperature",
#         "temp_air",
#     ]

#     ALL = [DATETIME] + WEATHER + HVAC


# class CACHE_DYD_COLUMNS:
#     WEATHER = ["T_out", "RH_out"]
#     DATETIME = "DateTime"
#     OCCUPANCY = [
#         "Thermostat_Motion",
#         "Remote_Sensor_1_Motion",
#         "Remote_Sensor_2_Motion",
#         "Remote_Sensor_3_Motion",
#         "Remote_Sensor_4_Motion",
#         "Remote_Sensor_5_Motion",
#         "Remote_Sensor_6_Motion",
#         "Remote_Sensor_7_Motion",
#         "Remote_Sensor_8_Motion",
#         "Remote_Sensor_9_Motion",
#         "Remote_Sensor_10_Motion",
#     ]
#     HVAC = [
#         "HvacMode",
#         "Event",
#         "Schedule",
#         "T_ctrl",
#         "T_stp_cool",
#         "T_stp_heat",
#         "Humidity",
#         "HumidityExpectedLow",
#         "HumidityExpectedHigh",
#         "auxHeat1",
#         "auxHeat2",
#         "auxHeat3",
#         "compCool1",
#         "compCool2",
#         "compHeat1",
#         "compHeat2",
#         "fan",
#         "Thermostat_Temperature",
#         "Remote_Sensor_1_Temperature",
#         "Remote_Sensor_2_Temperature",
#         "Remote_Sensor_3_Temperature",
#         "Remote_Sensor_4_Temperature",
#         "Remote_Sensor_5_Temperature",
#         "Remote_Sensor_6_Temperature",
#         "Remote_Sensor_7_Temperature",
#         "Remote_Sensor_8_Temperature",
#         "Remote_Sensor_9_Temperature",
#         "Remote_Sensor_10_Temperature",
#     ]

#     TEMPERATURE = [
#         "T_ctrl",
#         "T_stp_cool",
#         "T_stp_heat",
#         "Thermostat_Temperature",
#         "Remote_Sensor_1_Temperature",
#         "Remote_Sensor_2_Temperature",
#         "Remote_Sensor_3_Temperature",
#         "Remote_Sensor_4_Temperature",
#         "Remote_Sensor_5_Temperature",
#         "Remote_Sensor_6_Temperature",
#         "Remote_Sensor_7_Temperature",
#         "Remote_Sensor_8_Temperature",
#         "Remote_Sensor_9_Temperature",
#         "Remote_Sensor_10_Temperature",
#         "temp_air",
#     ]

#     INTERNAL_MAP = {DATETIME: "datetime", "Humidity": "Thermostat_Humidity"}

#     ALL = [DATETIME] + WEATHER + HVAC


# class HVAC_COLUMNS:
#     DATETIME = "datetime"

#     ALL = [DATETIME]


class EnergyPlusWeather:
    datetime_column = "datetime"
    # full = Spec(
    #     {
    #         "year": {
    #             "internal_name": "year",
    #             "dtype": "Float32",
    #             "channel": Channels.WEATHER,
    #             "unit": Units.CELSIUS,
    #         },
    #         "month": {
    #             "internal_name": "month",
    #             "dtype": "Float32",
    #             "channel": Channels.WEATHER,
    #             "unit": Units.RELATIVE_HUMIDITY,
    #         },
    #         "month": {
    #             "internal_name": "month",
    #             "dtype": "Float32",
    #             "channel": Channels.WEATHER,
    #             "unit": Units.RELATIVE_HUMIDITY,
    #         },
    #     }[

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

