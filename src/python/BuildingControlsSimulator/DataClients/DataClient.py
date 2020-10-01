# created by Tom Stesco tom.s@ecobee.com
import os
import logging

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

    # state variables
    sim_config = attr.ib(default=None)
    meta_gs_uri = attr.ib(default=None)
    start_utc = attr.ib(default=None)
    end_utc = attr.ib(default=None)
    eplus_fill_to_day_seconds = attr.ib(default=None)
    eplus_warmup_seconds = attr.ib(default=None)

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

        # truncate the data to desired simulation start and end time
        _data = _data[
            (_data[Internal.datetime_column] >= self.sim_config["start_utc"])
            & (_data[Internal.datetime_column] < self.sim_config["end_utc"])
        ].reset_index(drop=True)

        _expected_period = f"{self.sim_config['step_size_minutes']}M"
        # ffill first 15 minutes of missing data periods
        _data = DataClient.fill_missing_data(
            full_data=_data, expected_period=_expected_period,
        )

        # compute full_data_periods with only first 15 minutes ffilled
        self.full_data_periods = DataClient.get_full_data_periods(
            full_data=_data,
            expected_period=_expected_period,
            min_sim_period=self.sim_config["min_sim_period"],
        )

        _start_utc, _end_utc = self.get_simulation_period(
            expected_period=_expected_period
        )

        # add records for warmup period if needed
        _data = DataClient.add_null_records(
            df=_data,
            start_utc=_start_utc,
            end_utc=_end_utc,
            expected_period=_expected_period,
        )

        # drop records before and after full simulation time
        # end is less than
        _data = _data[
            (_data[Internal.datetime_column] >= _start_utc)
            & (_data[Internal.datetime_column] < _end_utc)
        ].reset_index(drop=True)

        # bfill to interpolate missing data
        # first and last records must be full because we used full data periods
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

    def get_simulation_period(self, expected_period):
        # set start and end times from full_data_periods and simulation config
        # take limiting period as start_utc and end_utc
        if self.sim_config["start_utc"] > self.full_data_periods[0][0]:
            self.start_utc = self.sim_config["start_utc"]
        else:
            logger.info(
                f"config start_utc={self.sim_config['start_utc']} is before "
                + f"first full data period={self.full_data_periods[0][0]}. "
                + "Simulation start_utc set to first full data period."
            )
            self.start_utc = self.full_data_periods[0][0]

        if self.sim_config["end_utc"] < self.full_data_periods[-1][-1]:
            self.end_utc = self.sim_config["end_utc"]
        else:
            logger.info(
                f"config end_utc={self.sim_config['end_utc']} is after "
                + f"last full data period={self.full_data_periods[-1][-1]}. "
                + "Simulation end_utc set to last full data period."
            )
            self.end_utc = self.full_data_periods[-1][-1]

        if self.end_utc < self.start_utc:
            raise ValueError(
                f"end_utc={self.end_utc} before start_utc={self.start_utc}.\n"
                + f"Set sim_config start_utc and end_utc within "
                + f"full_data_period: {self.full_data_periods[0][0]} to "
                + f"{self.full_data_periods[-1][-1]}"
            )

        _start_utc, _end_utc = DataClient.eplus_day_fill_simulation_time(
            start_utc=self.start_utc,
            end_utc=self.end_utc,
            expected_period=expected_period,
        )
        _minimum_warmup_seconds = 2 * 3600
        if (
            self.start_utc - _start_utc
        ).total_seconds() < _minimum_warmup_seconds:
            # attempt to enforce a minimum warmup time in EnergyPlus
            (
                _retry_start_utc,
                _retry_end_utc,
            ) = DataClient.eplus_day_fill_simulation_time(
                start_utc=self.start_utc
                - pd.Timedelta(seconds=_minimum_warmup_seconds),
                end_utc=self.end_utc,
                expected_period=expected_period,
            )
            if _retry_start_utc.year == _start_utc.year:
                _start_utc = _retry_start_utc
                _end_utc = _retry_end_utc

        self.start_utc = _start_utc
        self.end_utc = _end_utc

        return self.start_utc, self.end_utc

    @staticmethod
    def add_null_records(df, start_utc, end_utc, expected_period):
        rec = pd.Series(pd.NA, index=df.columns)

        should_resample = False
        if df[(df[Internal.datetime_column] == start_utc)].empty:
            # append record with start_utc time
            rec[Internal.datetime_column] = start_utc
            df = df.append(rec, ignore_index=True).sort_values(
                Internal.datetime_column
            )
            should_resample = True

        if df[(df[Internal.datetime_column] == end_utc)].empty:
            # append record with end_utc time
            rec[Internal.datetime_column] = end_utc
            df = df.append(rec, ignore_index=True).sort_values(
                Internal.datetime_column
            )
            should_resample = True

        if should_resample:
            # frequency rules have different str format
            _str_format_dict = {
                "M": "T",  # covert minutes formats
            }
            # replace last char using format conversion dict
            resample_freq = (
                expected_period[0:-1] + _str_format_dict[expected_period[-1]]
            )

            # resampling
            df = df.set_index(Internal.datetime_column)
            df = df.resample(resample_freq).asfreq()
            df = df.reset_index()

        return df

    @staticmethod
    def eplus_day_fill_simulation_time(start_utc, end_utc, expected_period):
        # EPlus requires that total simulation time be divisible by 86400 seconds
        # or whole days. EPlus also has some transient behaviour at t_init
        # adding time to beginning of simulation input data that will be
        # backfilled is more desirable than adding time to end of simulation
        # this time will not be included in the full_data_periods and thus
        # will not be considered during analysis
        add_timedelta = pd.Timedelta(days=(end_utc - start_utc).days + 1) - (
            end_utc - start_utc
        )

        # check if need to add time
        if add_timedelta >= pd.Timedelta(expected_period):
            # check if time available at start of year or end of year
            # EPlus requires single year simulations

            # fill beginning of simulation first because that helps with
            # transient behaviour
            beginning_timedelta = start_utc - pd.Timestamp(
                year=start_utc.year, month=1, day=1, tz="UTC"
            )
            if beginning_timedelta >= add_timedelta:
                # fill entirely in warmup of simulation
                start_utc = start_utc - add_timedelta
            else:
                # fill partially in beginning of simulation
                start_utc = start_utc - beginning_timedelta
                add_timedelta = add_timedelta - beginning_timedelta

                # fill in end of simulation
                # this actually does not need to be simulated, the simulation
                # can be stopped once the data periods are complete
                # only the seconds additionally for EPlus initialization are
                # needed
                ending_timedelta = (
                    pd.Timestamp(year=end_utc.year, month=1, day=1, tz="UTC")
                    - pd.Timedelta(expected_period)
                    - end_utc
                )
                if ending_timedelta >= add_timedelta:
                    # fill remainder entirely in ending of simulation
                    end_utc = end_utc + add_timedelta
                else:
                    # This shouldn't occur, should always be able to divide fully
                    raise ValueError(
                        f"start_utc={start_utc} to end_utc={end_utc} "
                        + " cannot be shaped to divisible by whole days required"
                        + " by EnergyPlus."
                    )
        return start_utc, end_utc

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

        if not fill_start_df.empty:
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
