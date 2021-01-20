# created by Tom Stesco tom.s@ecobee.com

import logging

import pytest
import pandas as pd
import os
import shutil

import attr

logger = logging.getLogger(__name__)


@attr.s(kw_only=True)
class Metric:

    dyd_map = attr.ib(
        default=[
            "datetime",
            "HvacMode",
            "Event",
            "Schedule",
            "T_ctrl",
            "T_stp_cool",
            "T_stp_heat",
            "Humidity",
            "HumidityExpectedLow",
            "HumidityExpectedHigh",
            "auxHeat1",
            "auxHeat2",
            "auxHeat3",
            "compCool1",
            "compCool2",
            "compHeat1",
            "compHeat2",
            "fan",
            "Thermostat_Temperature",
            "Thermostat_Motion",
            "Remote_Sensor_1_Temperature",
            "Remote_Sensor_1_Motion",
            "Remote_Sensor_2_Temperature",
            "Remote_Sensor_2_Motion",
            "Remote_Sensor_3_Temperature",
            "Remote_Sensor_3_Motion",
            "Remote_Sensor_4_Temperature",
            "Remote_Sensor_4_Motion",
            "Remote_Sensor_5_Temperature",
            "Remote_Sensor_5_Motion",
            "Remote_Sensor_6_Temperature",
            "Remote_Sensor_6_Motion",
            "Remote_Sensor_7_Temperature",
            "Remote_Sensor_7_Motion",
            "Remote_Sensor_8_Temperature",
            "Remote_Sensor_8_Motion",
            "Remote_Sensor_9_Temperature",
            "Remote_Sensor_9_Motion",
            "Remote_Sensor_10_Temperature",
            "Remote_Sensor_10_Motion",
        ]
    )

    ism_map = attr.ib(
        default=[
            "date_time",
            "Identifier",
            "DimThermostatID",
            "HvacMode",
            "SystemMode",
            "CalendarEvent",
            "Climate",
            "Temperature_ctrl",
            "TemperatureExpectedCool",
            "TemperatureExpectedHeat",
            "Humidity",
            "HumidityExpectedLow",
            "HumidityExpectedHigh",
            "unknown",
            "auxHeat1",
            "auxHeat2",
            "auxHeat3",
            "compCool1",
            "compCool2",
            "compHeat1",
            "compHeat2",
            "dehumidifier",
            "economizer",
            "fan",
            "humidifier",
            "ventilator",
            "auxWaterHeater",
            "compWaterHeater",
            "SensorTemp000",
            "SensorHum000",
            "SensorOcc000",
            "SensorName100",
            "SensorTemp100",
            "SensorOcc100",
            "SensorName101",
            "SensorTemp101",
            "SensorOcc101",
            "SensorName102",
            "SensorTemp102",
            "SensorOcc102",
            "SensorName103",
            "SensorTemp103",
            "SensorOcc103",
            "SensorName104",
            "SensorTemp104",
            "SensorOcc104",
            "SensorName105",
            "SensorTemp105",
            "SensorOcc105",
            "SensorName106",
            "SensorTemp106",
            "SensorOcc106",
            "SensorName107",
            "SensorTemp107",
            "SensorOcc107",
            "SensorName108",
            "SensorTemp108",
            "SensorOcc108",
            "SensorName109",
            "SensorTemp109",
            "SensorOcc109",
            "SensorName110",
            "SensorTemp110",
            "SensorOcc110",
            "SensorName111",
            "SensorTemp111",
            "SensorOcc111",
            "SensorName112",
            "SensorTemp112",
            "SensorOcc112",
            "SensorName113",
            "SensorTemp113",
            "SensorOcc113",
            "SensorName114",
            "SensorTemp114",
            "SensorOcc114",
            "SensorName115",
            "SensorTemp115",
            "SensorOcc115",
            "SensorName116",
            "SensorTemp116",
            "SensorOcc116",
            "SensorName117",
            "SensorTemp117",
            "SensorOcc117",
            "SensorName118",
            "SensorTemp118",
            "SensorOcc118",
            "SensorName119",
            "SensorTemp119",
            "SensorOcc119",
            "SensorName120",
            "SensorTemp120",
            "SensorOcc120",
            "SensorName121",
            "SensorTemp121",
            "SensorOcc121",
            "SensorName122",
            "SensorTemp122",
            "SensorOcc122",
            "SensorName123",
            "SensorTemp123",
            "SensorOcc123",
            "SensorName124",
            "SensorTemp124",
            "SensorOcc124",
            "SensorName125",
            "SensorTemp125",
            "SensorOcc125",
            "SensorName126",
            "SensorTemp126",
            "SensorOcc126",
            "SensorName127",
            "SensorTemp127",
            "SensorOcc127",
            "SensorName128",
            "SensorTemp128",
            "SensorOcc128",
            "SensorName129",
            "SensorTemp129",
            "SensorOcc129",
            "SensorName130",
            "SensorTemp130",
            "SensorOcc130",
            "SensorName131",
            "SensorTemp131",
            "SensorOcc131",
            "RSensor2Name100",
            "RSensor2Temp100",
            "RSensor2Occ100",
            "RSensor2Name101",
            "RSensor2Temp101",
            "RSensor2Occ101",
            "RSensor2Name102",
            "RSensor2Temp102",
            "RSensor2Occ102",
            "RSensor2Name103",
            "RSensor2Temp103",
            "RSensor2Occ103",
            "RSensor2Name104",
            "RSensor2Temp104",
            "RSensor2Occ104",
            "RSensor2Name105",
            "RSensor2Temp105",
            "RSensor2Occ105",
            "RSensor2Name106",
            "RSensor2Temp106",
            "RSensor2Occ106",
            "RSensor2Name107",
            "RSensor2Temp107",
            "RSensor2Occ107",
            "RSensor2Name108",
            "RSensor2Temp108",
            "RSensor2Occ108",
            "RSensor2Name109",
            "RSensor2Temp109",
            "RSensor2Occ109",
            "LightSwitchName100",
            "LightSwitchTemp100",
            "LightSwitchOcc100",
            "LightSwitchName101",
            "LightSwitchTemp101",
            "LightSwitchOcc101",
            "LightSwitchName102",
            "LightSwitchTemp102",
            "LightSwitchOcc102",
            "LightSwitchName103",
            "LightSwitchTemp103",
            "LightSwitchOcc103",
            "LightSwitchName104",
            "LightSwitchTemp104",
            "LightSwitchOcc104",
            "LightSwitchName105",
            "LightSwitchTemp105",
            "LightSwitchOcc105",
            "LightSwitchName106",
            "LightSwitchTemp106",
            "LightSwitchOcc106",
            "LightSwitchName107",
            "LightSwitchTemp107",
            "LightSwitchOcc107",
            "LightSwitchName108",
            "LightSwitchTemp108",
            "LightSwitchOcc108",
            "LightSwitchName109",
            "LightSwitchTemp109",
            "LightSwitchOcc109",
            "FeelsLikeControlOffset",
        ]
    )

    def HVAC_cycles(self, hvac_df):
        # assuming HVAC runtime cannot be less than 300s (5 minutes)
        min_cycle_time = 300
        min_time_btwn_cycles = 300

        # when ambiguous assume runtime is from previous cycle

        #
        # has less than full runtime
        # AND current runtime plus previous step runtime is geq min cycle time
        # AND next step runtime minus current runtime is leq min_time_btwn_cycles
        # OR
        # current period had runtime
        # AND next period is geq 20 minutes diff
        m_cool_stop = (
            (hvac_df.compCool1 < 300)
            & (
                (
                    hvac_df.compCool1 + hvac_df.compCool1.shift(periods=1)
                    >= min_cycle_time
                )
                | (hvac_df.compCool1.shift(periods=1).isnull())
            )
            & (
                (
                    hvac_df.compCool1 + hvac_df.compCool1.shift(periods=-1)
                    <= min_time_btwn_cycles
                )
                | (hvac_df.compCool1.shift(periods=-1).isnull())
            )
        ) | (
            (hvac_df.compCool1 > 0)
            & (
                hvac_df["datetime"].shift(-1) - hvac_df["datetime"]
                >= pd.Timedelta("20M")
            )
        )

        # has cool runtime
        # AND previous step had no runtime OR previous step had cycle stop
        m_cool_start = (hvac_df.compCool1 > 0) & (
            (hvac_df.compCool1.shift(periods=1) == 0)
            | hvac_df.compCool1.shift(periods=1).isnull()
            | (m_cool_stop.shift(1))
        )

        # create index for each cooling cycle
        hvac_df["cool_stop"] = (m_cool_stop).cumsum()
        hvac_df["cool_start"] = (m_cool_start).cumsum()
        hvac_df["xpt"] = (m_cool_stop | m_cool_start).cumsum()

        return hvac_df
