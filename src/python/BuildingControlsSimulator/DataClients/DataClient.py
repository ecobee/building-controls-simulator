# created by Tom Stesco tom.s@ecobee.com
import os
import logging
from collections.abc import Iterable

import attr
import pandas as pd
import numpy as np

from BuildingControlsSimulator.DataClients.DataSpec import Internal
from BuildingControlsSimulator.DataClients.SensorsChannel import SensorsChannel
from BuildingControlsSimulator.DataClients.HVACChannel import HVACChannel
from BuildingControlsSimulator.DataClients.WeatherChannel import WeatherChannel

logger = logging.getLogger(__name__)


@attr.s(kw_only=True)
class DataClient:

    # data channels
    hvac = attr.ib(default={})
    sensors = attr.ib(default={})
    weather = attr.ib(default={})

    # input variables
    nrel_dev_api_key = attr.ib(default=None)
    nrel_dev_email = attr.ib(default=None)
    archive_tmy3_meta = attr.ib(default=None)
    archive_tmy3_data_dir = attr.ib(
        default=os.environ.get("ARCHIVE_TMY3_DATA_DIR")
    )
    ep_tmy3_cache_dir = attr.ib(default=os.environ.get("EP_TMY3_CACHE_DIR"))
    simulation_epw_dir = attr.ib(default=os.environ.get("SIMULATION_EPW_DIR"))
    weather_dir = attr.ib(default=os.environ.get("WEATHER_DIR"))

    # state variabels
    meta_gs_uri = attr.ib(default=None)
    sources = attr.ib()

    def __attrs_post_init__(self):
        # first, post init class specification
        self.make_data_directories()

    def make_data_directories(self):
        os.makedirs(self.weather_dir, exist_ok=True)
        os.makedirs(self.archive_tmy3_data_dir, exist_ok=True)
        os.makedirs(self.ep_tmy3_cache_dir, exist_ok=True)
        os.makedirs(self.simulation_epw_dir, exist_ok=True)

    def get_data(self, sim_config):

        # check for invalid start/end combination
        invalid = sim_config[
            sim_config["end_utc"] <= sim_config["start_utc"]
        ]

        if not invalid.empty:
            raise ValueError(
                "sim_config contains invalid start_utc >= end_utc."
            )

        _data = {
            identifier: pd.DataFrame([], columns=[Internal.datetime_column])
            for identifier in sim_config.index
        }
        for _s in self.sources:
            # load from cache or download data from source
            _data_dict = _s.get_data(sim_config)
            for tstat, _df in _data_dict.items():
                # joining on datetime column with the initial empty df having
                # only the datetime_column causes new columns to be added
                # and handles missing data in any data sets
                if not _df.empty:
                    _data[tstat] = _data[tstat].merge(
                        _df, how="outer", on=Internal.datetime_column,
                    )
                else:
                    logging.info(
                        "EMPTY SOURCE: tstat={}, source={}".format(tstat, _s)
                    )
                    if _data[tstat].empty:
                        _data[tstat] = Internal.get_empty_df()

        # finally create the data channel objs for usage during simulation
        for identifier, tstat in sim_config.iterrows():

            self.hvac[identifier] = HVACChannel(
                data=_data[identifier][
                    [Internal.datetime_column]
                    + Internal.intersect_columns(
                        _data[identifier].columns, Internal.hvac.spec
                    )
                ],
                spec=Internal.hvac,
            )
            self.hvac[identifier].get_full_data_periods(expected_period="5M")

            self.sensors[identifier] = SensorsChannel(
                data=_data[identifier][
                    [Internal.datetime_column]
                    + Internal.intersect_columns(
                        _data[identifier].columns, Internal.sensors.spec
                    )
                ],
                spec=Internal.sensors,
            )
            self.sensors[identifier].get_full_data_periods(
                expected_period="5M"
            )

            self.weather[identifier] = WeatherChannel(
                data=_data[identifier][
                    [Internal.datetime_column]
                    + Internal.intersect_columns(
                        _data[identifier].columns, Internal.weather.spec
                    )
                ],
                spec=Internal.weather,
                archive_tmy3_data_dir=self.archive_tmy3_data_dir,
                ep_tmy3_cache_dir=self.ep_tmy3_cache_dir,
                simulation_epw_dir=self.simulation_epw_dir,
            )
            self.weather[identifier].get_full_data_periods(
                expected_period="5M"
            )

            # post-processing of data channels
            self.weather[identifier].make_epw_file(tstat=tstat)

    def get_metadata(self):
        return pd.read_csv(self.meta_gs_uri).drop_duplicates(
            subset=["Identifier"]
        )

    def get_simulation_data(self, sim_config):
        sim_hvac_data = {}
        sim_weather_data = {}
        for identifier, tstat in sim_config.iterrows():
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

