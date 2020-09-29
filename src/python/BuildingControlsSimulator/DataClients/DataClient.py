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
    full_data_periods = attr.ib(default=[])

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

    def get_data(self):
        # check for invalid start/end combination
        if self.sim_config["end_utc"] <= self.sim_config["start_utc"]:
            raise ValueError(
                "sim_config contains invalid start_utc >= end_utc."
            )
        # load from cache or download data from source
        _data = self.source.get_data(self.sim_config)
        _data = _data.sort_index()

        if _data.empty:
            logging.error(
                "EMPTY DATA SOURCE: \nsim_config={} \nsource={}\n".format(
                    self.sim_config, self.source
                )
            )
            _data = Internal.get_empty_df()

        # finally create the data channel objs for usage during simulation

        self.hvac = HVACChannel(
            data=_data[
                [Internal.datetime_column]
                + Internal.intersect_columns(_data.columns, Internal.hvac.spec)
            ],
            spec=Internal.hvac,
        )
        # self.hvac.get_full_data_periods(expected_period="5M")

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
        # self.sensors.get_full_data_periods(expected_period="5M")

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
        # self.weather.get_full_data_periods(expected_period="5M")

        # post-processing of data channels
        self.weather.make_epw_file(sim_config=self.sim_config)

        self.get_full_data_periods(full_data=_data, expected_period="5M")

    def get_metadata(self):
        return pd.read_csv(self.meta_gs_uri).drop_duplicates(
            subset=["Identifier"]
        )

    def get_full_data_periods(self, full_data, expected_period="5M"):
        """Set `sim_data` in each data channel with periods data exists in all
        channels.
        """

        # iterate through data sources
        # data_source_periods = [
        #     self.hvac.full_data_periods,
        #     self.sensors.full_data_periods,
        #     self.weather.full_data_periods,
        # ]
        null_check_cols = (
            self.hvac.spec.null_check_columns
            + self.sensors.spec.null_check_columns
            + self.weather.spec.null_check_columns
        )

        full_data = (
            full_data.dropna(
                axis=0, how="any", subset=null_check_cols
            ).drop_duplicates(ignore_index=True)
            # .reset_index(drop=True)
            .sort_values(self.hvac.spec.datetime_column, ascending=True)
        )

        diffs = full_data[self.hvac.spec.datetime_column].diff()

        breakpoint()

        # check for missing records?
        missing_start_idx = diffs[
            diffs > pd.to_timedelta(expected_period)
        ].index.to_list()

        missing_end_idx = [idx - 1 for idx in missing_start_idx] + [
            len(diffs) - 1
        ]
        missing_start_idx = [0] + missing_start_idx
        # ensoure ascending before zip
        missing_start_idx.sort()
        missing_end_idx.sort()

        _full_data_periods = list(
            zip(
                pd.to_datetime(
                    full_data[self.hvac.spec.datetime_column][
                        missing_start_idx
                    ].values,
                    utc=True,
                ),
                pd.to_datetime(
                    full_data[self.hvac.pec.datetime_column][
                        missing_end_idx
                    ].values,
                    utc=True,
                ),
            )
        )

        breakpoint()
