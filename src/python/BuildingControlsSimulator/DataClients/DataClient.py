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
from BuildingControlsSimulator.DataClients.DataSource import DataSource

logger = logging.getLogger(__name__)


@attr.s(kw_only=True)
class DataClient:

    # data channels
    hvac = attr.ib(default={})
    sensors = attr.ib(default={})
    weather = attr.ib(default={})

    # input variables
    source = attr.ib(validator=attr.validators.instance_of(DataSource))
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
    sim_config = attr.ib(default=None)
    meta_gs_uri = attr.ib(default=None)

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
        if sim_config["end_utc"] <= sim_config["start_utc"]:
            raise ValueError(
                "sim_config contains invalid start_utc >= end_utc."
            )
        # load from cache or download data from source
        _data = self.source.get_data(sim_config)

        if _data.empty:
            logging.error(
                "EMPTY DATA SOURCE: \nsim_config={} \nsource={}\n".format(
                    sim_config, self.source
                )
            )
            if _data.empty:
                _data = Internal.get_empty_df()

        # finally create the data channel objs for usage during simulation

        self.hvac = HVACChannel(
            data=_data[
                [Internal.datetime_column]
                + Internal.intersect_columns(_data.columns, Internal.hvac.spec)
            ],
            spec=Internal.hvac,
        )
        self.hvac.get_full_data_periods(expected_period="5M")

        self.sensors = SensorsChannel(
            data=_data[
                [Internal.datetime_column]
                + Internal.intersect_columns(
                    _data.columns, Internal.sensors.spec
                )
            ],
            spec=Internal.sensors,
        )
        self.sensors.drop_unused_room_sensors()
        self.sensors.get_full_data_periods(expected_period="5M")

        self.weather = WeatherChannel(
            data=_data[
                [Internal.datetime_column]
                + Internal.intersect_columns(
                    _data.columns, Internal.weather.spec
                )
            ],
            spec=Internal.weather,
            archive_tmy3_data_dir=self.archive_tmy3_data_dir,
            ep_tmy3_cache_dir=self.ep_tmy3_cache_dir,
            simulation_epw_dir=self.simulation_epw_dir,
        )
        self.weather.get_full_data_periods(expected_period="5M")

        # post-processing of data channels
        self.weather.make_epw_file(sim_config=sim_config)

        self.get_simulation_data(sim_config)

    def get_metadata(self):
        return pd.read_csv(self.meta_gs_uri).drop_duplicates(
            subset=["Identifier"]
        )

    def get_simulation_data(self, sim_config):
        """Set `sim_data` in each data channel with periods data exists in all
        channels.
        """
        self.hvac.sim_data = []
        self.weather.sim_data = []

        # iterate through data sources
        data_source_periods = [
            self.hvac.full_data_periods,
            self.weather.full_data_periods,
            self.sensors.full_data_periods,
        ]

        # check for missing data sources
        if all([len(d) != 0 for d in data_source_periods]):
            # set period start of simulation time
            p_start = sim_config.start_utc
            p_end = sim_config.start_utc
            # create list of data source idxs to keep track of place for each
            ds_idx = [0 for d in data_source_periods]
            data_periods = []
            end_time = np.min([d[-1][1] for d in data_source_periods])
            while p_start < end_time:
                ds_p_start = []
                ds_p_end = []

                for i, d in enumerate(data_source_periods):
                    if ds_idx[i] < len(d) - 1 and p_start >= d[ds_idx[i]][1]:
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
                if (p_end - p_start) > sim_config.min_sim_period:
                    for _data_channel in [
                        self.hvac,
                        self.sensors,
                        self.weather,
                    ]:
                        _data_channel.sim_data.append(
                            _data_channel.data[
                                (
                                    _data_channel.data[
                                        _data_channel.spec.datetime_column
                                    ]
                                    >= p_start
                                )
                                & (
                                    _data_channel.data[
                                        _data_channel.spec.datetime_column
                                    ]
                                    <= p_end
                                )
                            ]
                        )
        else:
            logger.info("No valid simulation periods.")

