# created by Tom Stesco tom.s@ecobee.com
import os
import logging
from abc import ABC, abstractmethod
from collections.abc import Iterable

import attr
import pandas as pd
import numpy as np

logger = logging.getLogger(__name__)


@attr.s(kw_only=True)
class DataClient(ABC):

    local_cache = attr.ib(default=None)
    gcs_cache = attr.ib(default=None)

    # data channels
    hvac = attr.ib(default={})
    sensors = attr.ib(default={})
    weather = attr.ib(default={})

    @abstractmethod
    def get_data(self, tstat_sim_config):
        pass

    def make_tstat_sim_config(
        self,
        identifier,
        latitude,
        longitude,
        start_utc,
        end_utc,
        min_sim_period,
        min_chunk_period,
    ):
        # first make sure identifier has a len()
        if not isinstance(identifier, Iterable):
            identifier = [identifier]

        # broadcast single values to lists of len(identifier)
        (
            latitude,
            longitude,
            start_utc,
            end_utc,
            min_sim_period,
            min_chunk_period,
        ) = [
            [v] * len(identifier)
            if (not isinstance(v, Iterable) or isinstance(v, str))
            else v
            for v in [
                latitude,
                longitude,
                start_utc,
                end_utc,
                min_sim_period,
                min_chunk_period,
            ]
        ]

        # parse and validate input
        for i in range(len(identifier)):
            if not isinstance(latitude[i], float):
                raise ValueError(
                    f"latitude[{i}]: {latitude[i]} is not a float."
                )
            if not isinstance(longitude[i], float):
                raise ValueError(
                    f"longitude[{i}]: {longitude[i]} is not a float."
                )
            # convert str to datetime utc
            if isinstance(start_utc[i], str):
                start_utc[i] = pd.Timestamp(start_utc[i], tz="utc")
            if isinstance(end_utc[i], str):
                end_utc[i] = pd.Timestamp(end_utc[i], tz="utc")

            if not isinstance(start_utc[i], pd.Timestamp):
                raise ValueError(
                    f"start_utc[{i}]: {start_utc[i]} is not convertable to pd.Timestamp."
                )
            if not isinstance(end_utc[i], pd.Timestamp):
                raise ValueError(
                    f"end_utc[{i}]: {end_utc[i]} is not convertable to pd.Timestamp."
                )

            # convert str to timedelta
            if isinstance(min_sim_period[i], str):
                min_sim_period[i] = pd.Timedelta(min_sim_period[i])
            if isinstance(min_chunk_period[i], str):
                min_chunk_period[i] = pd.Timedelta(min_chunk_period[i])

            if not isinstance(min_sim_period[i], pd.Timedelta):
                raise ValueError(
                    f"min_sim_period[{i}]: {min_sim_period[i]} is not convertable to pd.Timedelta."
                )
            if not isinstance(min_chunk_period[i], pd.Timedelta):
                raise ValueError(
                    f"min_chunk_period[{i}]: {min_chunk_period[i]} is not convertable to pd.Timedelta."
                )

        _df = pd.DataFrame.from_dict(
            {
                "identifier": identifier,
                "latitude": latitude,
                "longitude": longitude,
                "start_utc": start_utc,
                "end_utc": end_utc,
                "min_sim_period": min_sim_period,
                "min_chunk_period": min_chunk_period,
            }
        ).set_index("identifier")

        return _df

    def get_simulation_data(self, tstat_sim_config):
        sim_hvac_data = {}
        sim_weather_data = {}
        for identifier, tstat in tstat_sim_config.iterrows():
            sim_hvac_data[identifier] = []
            sim_weather_data[identifier] = []

            # iterate through data sources
            data_source_periods = [
                self.hvac[identifier].full_data_periods,
                self.weather[identifier].full_data_periods,
            ]

            # check for missing data sources
            if all([len(d) != 0 for d in data_source_periods]):
                # set period start of simulation time
                p_start = tstat.start_utc
                p_end = tstat.start_utc
                # create list of data source idxs to keep track of place for each
                ds_idx = [0 for d in data_source_periods]
                data_periods = []
                end_time = np.min([d[-1][1] for d in data_source_periods])
                while p_start < end_time:
                    ds_p_start = []
                    ds_p_end = []

                    for i, d in enumerate(data_source_periods):
                        if (
                            ds_idx[i] < len(d) - 1
                            and p_start >= d[ds_idx[i]][1]
                        ):
                            # increment ds idx if period start is past end of ds period
                            ds_idx[i] += 1

                        ds_p_start.append(d[ds_idx[i]][0])
                        ds_p_end.append(d[ds_idx[i]][1])

                    p_start = np.max(ds_p_start)
                    p_end = np.min(ds_p_end)
                    data_periods.append((p_start, p_end))
                    # advance time period
                    p_start = p_end

                for p_start, p_end in data_periods:
                    if (p_end - p_start) > tstat.min_sim_period:
                        sim_hvac_data[identifier].append(
                            self.hvac[identifier].data[
                                (
                                    self.hvac[identifier].data[
                                        self.hvac[
                                            identifier
                                        ].spec.datetime_column
                                    ]
                                    >= p_start
                                )
                                & (
                                    self.hvac[identifier].data[
                                        self.hvac[
                                            identifier
                                        ].spec.datetime_column
                                    ]
                                    <= p_end
                                )
                            ]
                        )

                        sim_weather_data[identifier].append(
                            self.weather[identifier].data[
                                (
                                    self.weather[identifier].data[
                                        self.weather[
                                            identifier
                                        ].spec.datetime_column
                                    ]
                                    >= p_start
                                )
                                & (
                                    self.weather[identifier].data[
                                        self.weather[
                                            identifier
                                        ].spec.datetime_column
                                    ]
                                    <= p_end
                                )
                            ]
                        )

        return sim_hvac_data, sim_weather_data

    @staticmethod
    def make_data_directories():
        os.makedirs(os.environ.get("WEATHER_DIR"), exist_ok=True)
        os.makedirs(os.environ.get("ARCHIVE_TMY3_DATA_DIR"), exist_ok=True)
        os.makedirs(os.environ.get("EP_TMY3_CACHE_DIR"), exist_ok=True)
        os.makedirs(os.environ.get("SIMULATION_EPW_DIR"), exist_ok=True)
