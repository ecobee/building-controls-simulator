# created by Tom Stesco tom.s@ecobee.com

import logging

import pandas as pd
import attr
import numpy as np

from BuildingControlsSimulator.DataClients.HVACSource import HVACSource
from BuildingControlsSimulator.DataClients.GCSDataSource import GCSDataSource


logger = logging.getLogger(__name__)


@attr.s(kw_only=True)
class DYDHVACSource(GCSDataSource, HVACSource):

    local_data_dir = attr.ib(default=None)

    # list of columns
    dyd_datetime_column = attr.ib(default="DateTime")
    weather_columns = attr.ib(default=["T_out", "RH_out"])
    hvac_columns = attr.ib(
        default=[
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

    temperatrue_columns = attr.ib(
        default=[
            "T_ctrl",
            "T_stp_cool",
            "T_stp_heat",
            "Thermostat_Temperature",
            "Remote_Sensor_1_Temperature",
            "Remote_Sensor_2_Temperature",
            "Remote_Sensor_3_Temperature",
            "Remote_Sensor_4_Temperature",
            "Remote_Sensor_5_Temperature",
            "Remote_Sensor_6_Temperature",
            "Remote_Sensor_7_Temperature",
            "Remote_Sensor_8_Temperature",
            "Remote_Sensor_9_Temperature",
            "Remote_Sensor_10_Temperature",
        ]
    )

    data = attr.ib(default=None)

    weather_data = attr.ib(default=None)

    def __attrs_post_init__(self):
        # DYD contains hvac and weather data
        self.expected_columns = (
            [self.dyd_datetime_column]
            + self.hvac_columns
            + self.weather_columns
        )

    def get_data(self, tstat_sim_config):
        """
        """
        # get all data from DYD cache
        all_data = self.get_cache(tstat_sim_config)

        self.weather_data = {}
        self.data = {}
        self.full_data_periods = {}
        for tstat_id, data in all_data.items():
            # weather will be further processed by DYDWeatherSource
            self.weather_data[tstat_id] = data[
                [self.dyd_datetime_column] + self.weather_columns
            ]

            # normalize data to internal format
            self.data[tstat_id] = self.to_internal_format(
                data[[self.dyd_datetime_column] + self.hvac_columns]
            )

            # find consecutive periods of data
            self.full_data_periods[tstat_id] = self.get_full_data_periods(
                self.data[tstat_id]
            )

    def get_empty_hvac_df(self):
        return pd.DataFrame(
            [],
            columns=[self.dyd_datetime_column]
            + self.hvac_columns
            + self.weather_columns,
        )

    def to_internal_format(self, df):
        df = df.rename(columns=self.hvac_column_map)

        # set datetime column, DYD is in UTC
        df[self.datetime_column] = pd.to_datetime(
            df[self.datetime_column], utc=True
        )

        # convert all temperatures to degrees Celcius, DYD is in Fahrenheit
        for temp_col in self.temperatrue_columns:
            df[temp_col] = DYDHVACSource.F2C(df[temp_col])
        df = df.sort_values(by=self.datetime_column, ascending=True)
        return df

    def get_cache(self, tstat_sim_config):

        cache_dict = {}
        for identifier, tstat in tstat_sim_config.iterrows():

            gs_uri_partial = f"{self.gcs_uri_base}/{tstat.start_utc.year}"

            # read cache
            try:
                cache_dict[identifier] = pd.read_csv(
                    f"{gs_uri_partial}/{identifier}.csv.zip",
                    compression="zip",
                )
            except FileNotFoundError:
                # file not found in DYD
                logging.error(
                    (
                        f"File: {gs_uri_partial}/{identifier}.csv.zip",
                        " not found in DYD dataset.",
                    )
                )
                cache_dict[identifier] = self.get_empty_hvac_df()

            # check cache contains all expected columns
            if any(
                [
                    c not in cache_dict[identifier].columns
                    for c in self.expected_columns
                ]
            ):
                logging.error(f"identifier={identifier} has missing columns.")

        return cache_dict

    def get_full_data_periods(self, df):
        # if df has no records then there are no full_data_periods
        full_data_periods = []
        if len(df) > 0:
            df = df.sort_values("datetime", ascending=True)
            # drop records that are incomplete
            df = df[~df["HvacMode"].isnull()].reset_index()

            diffs = df[self.datetime_column].diff()

            # check for missing records
            missing_start_idx = diffs[
                diffs > pd.to_timedelta("5M")
            ].index.to_list()

            missing_end_idx = [idx - 1 for idx in missing_start_idx] + [
                len(df) - 1
            ]
            missing_start_idx = [0] + missing_start_idx
            # ensoure ascending before zip
            missing_start_idx.sort()
            missing_end_idx.sort()

            full_data_periods = list(
                zip(
                    pd.to_datetime(
                        df.datetime[missing_start_idx].values, utc=True
                    ),
                    pd.to_datetime(
                        df.datetime[missing_end_idx].values, utc=True
                    ),
                )
            )

        return full_data_periods

    def put_cache(self):
        pass
