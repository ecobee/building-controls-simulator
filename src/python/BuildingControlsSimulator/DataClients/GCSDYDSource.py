# created by Tom Stesco tom.s@ecobee.com

import logging

import pandas as pd
import attr
import numpy as np

from BuildingControlsSimulator.DataClients.HVACSource import HVACSource
from BuildingControlsSimulator.DataClients.GCSDataSource import GCSDataSource
from BuildingControlsSimulator.DataClients.DataSpec import (
    Internal,
    FlatFiles,
    # DYD,
)

logger = logging.getLogger(__name__)


@attr.s(kw_only=True)
class GCSHVACSource(GCSDataSource, HVACSource):

    local_data_dir = attr.ib(default=None)

    # list of columns
    input_datetime_column = attr.ib()
    weather_columns = attr.ib()
    hvac_columns = attr.ib()
    temperature_columns = attr.ib()
    internal_column_map = attr.ib()
    data_spec = attr.ib()

    data = attr.ib(default=None)
    weather_data = attr.ib(default=None)

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
                [self.input_datetime_column]
                + self.data_spec.get_columns(self.data_spec.weather_spec)
            ]

            # normalize data to internal format
            self.data[tstat_id] = self.to_internal_format(
                data[[self.input_datetime_column] + self.data_spec.get_columns(self.data_spec.hvac_spec)
            )

            # find consecutive periods of data
            self.full_data_periods[tstat_id] = self.get_full_data_periods(
                self.data[tstat_id]
            )

    def get_empty_hvac_df(self):
        return pd.DataFrame([], columns=self.all_columns,)

    def to_internal_format(self, df):
        Internal.convert_to_internal(df=df, spec=self.spec)
        df = df.rename(columns=self.internal_column_map)

        # set datetime column, DYD is in UTC
        df[self.datetime_column] = pd.to_datetime(
            df[self.datetime_column], utc=True, infer_datetime_format=True
        )

        # convert all temperatures to degrees Celcius, DYD is in Fahrenheit
        for temp_col in [
            c for c in self.temperature_columns if c in self.all_columns
        ]:
            df[temp_col] = DYDHVACSource.F2C(df[temp_col])
        df = df.sort_values(by=self.datetime_column, ascending=True)
        return df

    def get_cache(self, tstat_sim_config):

        cache_dict = {}
        for identifier, tstat in tstat_sim_config.iterrows():

            # gs_uri_partial = f"{self.gcs_uri_base}/{tstat.start_utc.year}"

            # read cache
            try:
                cache_dict[identifier] = pd.read_csv(
                    tstat.gcs_uri,
                    usecols=spec.get_columns(spec.full),
                    dtype=spec.get_spec_dtype_mapper(spec.full),
                )
            except FileNotFoundError:
                # file not found in DYD
                logging.error(
                    (f"File: {tstat.gcs_uri}", " not found in DYD dataset.",)
                )
                cache_dict[identifier] = self.get_empty_hvac_df()

            cache_dict[identifier] = cache_dict[identifier].astype(
                spec.get_spec_dtype_mapper(spec.full)
            )

            # check cache contains all expected columns
            if any(
                [
                    c not in cache_dict[identifier].columns
                    for c in self.all_columns
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


@attr.s(kw_only=True)
class DYDHVACSource(GCSHVACSource):

    # list of columns
    input_datetime_column = attr.ib(default=CACHE_DYD_COLUMNS.DATETIME)
    weather_columns = attr.ib(default=CACHE_DYD_COLUMNS.WEATHER)
    hvac_columns = attr.ib(default=CACHE_DYD_COLUMNS.HVAC)
    temperature_columns = attr.ib(default=CACHE_DYD_COLUMNS.TEMPERATURE)
    internal_column_map = attr.ib(default=CACHE_DYD_COLUMNS.INTERNAL_MAP)
    spec = attr.ib(default=DYD)


@attr.s(kw_only=True)
class ISMHVACSource(GCSHVACSource):

    # list of columns
    input_datetime_column = attr.ib(default=CACHE_ISM_COLUMNS.DATETIME)
    weather_columns = attr.ib(default=CACHE_ISM_COLUMNS.WEATHER)
    hvac_columns = attr.ib(default=CACHE_ISM_COLUMNS.HVAC)
    temperature_columns = attr.ib(default=CACHE_ISM_COLUMNS.TEMPERATURE)
    internal_column_map = attr.ib(default=CACHE_ISM_COLUMNS.INTERNAL_MAP)
    spec = attr.ib(default=FlatFiles)
