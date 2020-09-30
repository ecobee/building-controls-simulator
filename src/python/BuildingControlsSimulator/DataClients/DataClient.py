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
    hvac = attr.ib(default=None)
    sensors = attr.ib(default=None)
    weather = attr.ib(default=None)
    full_data_periods = attr.ib(default=[])

    # input variables
    source = attr.ib(validator=attr.validators.instance_of(DataSource))
    nrel_dev_api_key = attr.ib(default=None)
    nrel_dev_email = attr.ib(default=None)
    archive_tmy3_dir = attr.ib(default=os.environ.get("ARCHIVE_TMY3_DIR"))
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

        _data = _data.drop_duplicates(ignore_index=True).reset_index(drop=True)
        _data = _data.sort_values(Internal.datetime_column, ascending=True)

        # ffill first 15 minutes of missing data
        _data = DataClient.fill_missing_data(
            full_data=_data,
            expected_period=f"{self.sim_config['step_size_minutes']}M",
        )

        # compute full_data_periods with only first 15 minutes ffilled
        self.full_data_periods = DataClient.get_full_data_periods(
            full_data=_data,
            expected_period=f"{self.sim_config['step_size_minutes']}M",
            min_sim_period=self.sim_config["min_sim_period"],
        )

        # remove nulls before first and after last full_data_period
        _data = _data[
            (_data[Internal.datetime_column] >= self.full_data_periods[0][0])
        ]

        # bfill remaining missing data
        _data = _data.fillna(method="bfill", limit=None)

        # finally create the data channel objs for usage during simulation

        self.hvac = HVACChannel(
            data=_data[
                [Internal.datetime_column]
                + Internal.intersect_columns(_data.columns, Internal.hvac.spec)
            ],
            spec=Internal.hvac,
        )

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

        self.weather = WeatherChannel(
            data=_data[
                [Internal.datetime_column]
                + Internal.intersect_columns(
                    _data.columns, Internal.weather.spec
                )
            ],
            spec=Internal.weather,
            archive_tmy3_dir=self.archive_tmy3_dir,
            archive_tmy3_data_dir=self.archive_tmy3_data_dir,
            ep_tmy3_cache_dir=self.ep_tmy3_cache_dir,
            simulation_epw_dir=self.simulation_epw_dir,
        )

        # post-processing of weather channel for EnergyPlus usage
        self.weather.make_epw_file(sim_config=self.sim_config)

    def get_metadata(self):
        return pd.read_csv(self.meta_gs_uri).drop_duplicates(
            subset=["Identifier"]
        )

    @staticmethod
    def get_full_data_periods(
        full_data, expected_period="5M", min_sim_period="7D"
    ):
        """Get full data periods. These are the periods for which there is data
        on all channels. Preliminary forward filling of the data is used to 
        fill small periods of missing data where padding values is advantageous
        for examplem the majority of missing data periods are less than 15 minutes
        (3 message intervals).

        The remaining missing data is back filled after the full_data_periods are
        computed to allow the simulations to run continously. Back fill is used
        because set point changes during the missing data period should be 
        assumed to be not in tracking mode and in regulation mode after greater
        than 
        """

        if full_data.empty:
            return []

        # compute time deltas between records
        diffs = full_data.dropna(
            axis="rows", subset=Internal.full.null_check_columns
        )[Internal.datetime_column].diff()

        # seperate periods by missing data
        periods_df = diffs[
            diffs > pd.to_timedelta(expected_period)
        ].reset_index()

        # make df of periods
        periods_df["start"] = full_data.loc[
            periods_df["index"], Internal.datetime_column
        ].reset_index(drop=True)

        periods_df["end"] = periods_df["start"] - periods_df[1]

        periods_df = periods_df.drop(axis="columns", columns=["index", 1])

        # append start and end datetimes from full_data
        periods_df.loc[len(periods_df)] = [
            pd.NA,
            full_data.loc[len(full_data) - 1, Internal.datetime_column],
        ]
        periods_df["start"] = periods_df["start"].shift(1)
        periods_df.loc[0, "start"] = full_data.loc[0, Internal.datetime_column]

        # only include full_data_periods that are geq min_sim_period
        # convert all np.arrays to lists for ease of use
        _full_data_periods = [
            list(rec)
            for rec in periods_df[
                periods_df["end"] - periods_df["start"]
                >= pd.Timedelta(min_sim_period)
            ].to_numpy()
        ]

        return _full_data_periods

    @staticmethod
    def fill_missing_data(
        full_data, expected_period, limit=3, method="ffill",
    ):
        """Fill periods of missing data within limit using method.
        Periods larger than limit will not be partially filled."""
        if full_data.empty:
            return full_data

        # frequency rules have different str format
        _str_format_dict = {
            "M": "T",  # covert minutes formats
        }
        # replace last char using format conversion dict
        resample_freq = (
            expected_period[0:-1] + _str_format_dict[expected_period[-1]]
        )
        # resample to add any timesteps that are fully missing
        full_data = full_data.set_index(Internal.datetime_column)
        full_data = full_data.resample(resample_freq).asfreq()
        full_data = full_data.reset_index()

        # compute timesteps between steps of data
        diffs = full_data.dropna(
            axis="rows", subset=Internal.full.null_check_columns
        )[Internal.datetime_column].diff()

        fill_start_df = (
            (
                diffs[
                    (diffs > pd.to_timedelta(expected_period))
                    & (diffs <= pd.to_timedelta(expected_period) * limit)
                ]
                / pd.Timedelta(expected_period)
            )
            .astype("Int64")
            .reset_index()
        )
        # take idxs with missing data and one record on either side to allow
        # for ffill and bfill methods to work generally
        fill_idxs = []
        for idx, num_missing in fill_start_df.to_numpy():
            fill_idxs = fill_idxs + [
                i for i in range(idx - (num_missing), idx + 1)
            ]

        # fill exact idxs that are missing using method
        full_data.iloc[fill_idxs] = full_data.iloc[fill_idxs].fillna(
            method=method
        )

        return full_data
