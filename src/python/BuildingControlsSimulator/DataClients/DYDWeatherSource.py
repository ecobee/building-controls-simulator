# created by Tom Stesco tom.s@ecobee.com

import os
import logging

import pandas as pd
import attr
import numpy as np

from BuildingControlsSimulator.DataClients.WeatherSource import WeatherSource
from BuildingControlsSimulator.DataClients.GCSDataSource import GCSDataSource

logger = logging.getLogger(__name__)


@attr.s(kw_only=True)
class DYDWeatherSource(GCSDataSource, WeatherSource):

    data_source_name = attr.ib(default="dyd")

    def get_data(self, tstat_sim_config, weather_data):
        """
        """

        # start with input data, DYD weather data is joined with HVAC
        self.data = weather_data

        self.full_data_periods = {}
        for identifier, tstat in tstat_sim_config.iterrows():
            # should already be localized to UTC (DYD is in UTC)
            # rename to epw_columns
            self.data[identifier].rename(
                columns=self.epw_column_map, inplace=True
            )

            # if empty weather dataframe skip epw processing
            if len(self.data[identifier]) > 0:

                fill_epw_fpath, fill_epw_fname = self.get_epw_from_nrel(
                    tstat.latitude, tstat.longitude
                )

                self.epw_fpaths[identifier] = os.path.join(
                    self.simulation_epw_dir,
                    f"{self.data_source_name}_{tstat.start_utc.year}_{identifier}_{fill_epw_fname}",
                )
                if True:
                    # if not os.path.exists(self.epw_fpaths[identifier]):
                    (
                        fill_epw_data,
                        self.epw_meta[identifier],
                        meta_lines,
                    ) = self.read_epw(fill_epw_fpath)

                    # fill any missing fields in epw
                    # need to pass in original dyd datetime column name
                    self.epw_data[identifier] = self.fill_epw(
                        self.data[identifier],
                        fill_epw_data,
                        datetime_column="DateTime",
                    )

                    # save to file
                    self.to_epw(
                        epw_data=self.epw_data[identifier],
                        meta=self.epw_meta[identifier],
                        meta_lines=meta_lines,
                        fpath=self.epw_fpaths[identifier],
                    )

            self.full_data_periods[identifier] = self.get_full_data_periods(
                self.data[identifier]
            )

    def get_full_data_periods(self, df):
        # if df has no records then there are no full_data_periods
        full_data_periods = []
        if len(df) > 0:
            df = df.sort_values("datetime", ascending=True)
            # drop records that are incomplete
            df = df[~df["temp_air"].isnull()].reset_index()

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

    def get_cache(self):
        pass

    def put_cache(self):
        pass
