# created by Tom Stesco tom.s@ecobee.com
import os
import logging

# import pkg_resources
from datetime import datetime

import attr
import pandas as pd
import numpy as np

from BuildingControlsSimulator.DataClients.DataStates import (
    UNITS,
    CHANNELS,
    STATES,
)
from BuildingControlsSimulator.Conversions.Conversions import Conversions
from BuildingControlsSimulator.DataClients.DataSpec import (
    Internal,
    FlatFilesSpec,
    DonateYourDataSpec,
    convert_spec,
)
from BuildingControlsSimulator.DataClients.DateTimeChannel import DateTimeChannel
from BuildingControlsSimulator.DataClients.ThermostatChannel import ThermostatChannel
from BuildingControlsSimulator.DataClients.EquipmentChannel import EquipmentChannel
from BuildingControlsSimulator.DataClients.SensorsChannel import SensorsChannel
from BuildingControlsSimulator.DataClients.WeatherChannel import WeatherChannel
from BuildingControlsSimulator.DataClients.DataSource import DataSource
from BuildingControlsSimulator.DataClients.DataDestination import DataDestination
from BuildingControlsSimulator.DataClients.LocalDestination import LocalDestination


logger = logging.getLogger(__name__)


@attr.s(kw_only=True)
class DataClient:

    # data channels
    thermostat = attr.ib(default=None)
    equipment = attr.ib(default=None)
    sensors = attr.ib(default=None)
    weather = attr.ib(default=None)
    datetime = attr.ib(default=None)
    full_data_periods = attr.ib(factory=list)

    # input variables
    source = attr.ib(validator=attr.validators.instance_of(DataSource))
    destination = attr.ib(validator=attr.validators.instance_of(DataDestination))
    nrel_dev_api_key = attr.ib(default=os.environ.get("NREL_DEV_API_KEY"))
    nrel_dev_email = attr.ib(default=os.environ.get("NREL_DEV_EMAIL"))
    archive_tmy3_dir = attr.ib(default=os.environ.get("ARCHIVE_TMY3_DIR"))
    archive_tmy3_meta = attr.ib(default=os.environ.get("ARCHIVE_TMY3_META"))
    archive_tmy3_data_dir = attr.ib(default=os.environ.get("ARCHIVE_TMY3_DATA_DIR"))
    ep_tmy3_cache_dir = attr.ib(default=os.environ.get("EP_TMY3_CACHE_DIR"))
    nsrdb_cache_dir = attr.ib(default=os.environ.get("NSRDB_CACHE_DIR"))
    simulation_epw_dir = attr.ib(default=os.environ.get("SIMULATION_EPW_DIR"))
    weather_dir = attr.ib(default=os.environ.get("WEATHER_DIR"))
    weather_forecast_source = attr.ib(default="perfect")
    epw_path = attr.ib(default=None)

    # state variables
    sim_config = attr.ib(default=None)
    start_utc = attr.ib(default=None)
    end_utc = attr.ib(default=None)
    eplus_fill_to_day_seconds = attr.ib(default=None)
    eplus_warmup_seconds = attr.ib(default=None)
    internal_spec = attr.ib(factory=Internal)
    forecast_from_measured = attr.ib(default=True)
    has_data = attr.ib(default=False)

    def __attrs_post_init__(self):
        # first, post init class specification
        self.make_data_directories()

    def make_data_directories(self):
        os.makedirs(self.weather_dir, exist_ok=True)
        os.makedirs(self.archive_tmy3_data_dir, exist_ok=True)
        os.makedirs(self.ep_tmy3_cache_dir, exist_ok=True)
        os.makedirs(self.nsrdb_cache_dir, exist_ok=True)
        os.makedirs(self.simulation_epw_dir, exist_ok=True)
        if self.source.local_cache:
            os.makedirs(
                os.path.join(
                    self.source.local_cache,
                    self.source.operator_name,
                    self.source.source_name,
                ),
                exist_ok=True,
            )
        if self.destination.local_cache:
            os.makedirs(
                os.path.join(
                    self.destination.local_cache,
                    self.destination.operator_name,
                ),
                exist_ok=True,
            )

    def get_data(self):
        # check if data has already been fetched by another simulation
        if self.has_data:
            return

        # check for invalid start/end combination
        if self.sim_config["end_utc"] <= self.sim_config["start_utc"]:
            raise ValueError("sim_config contains invalid start_utc >= end_utc.")
        # load from cache or download data from source
        _data = self.source.get_data(self.sim_config)
        if _data.empty:
            logger.error(
                "EMPTY DATA SOURCE: \nsim_config={} \nsource={}\n".format(
                    self.sim_config, self.source
                )
            )
            _data = self.internal_spec.get_empty_df()

        # remove any fully duplicated records
        _data = _data.drop_duplicates(ignore_index=True)

        # remove multiple records for same datetime
        # there may also be multiple entries for same exact datetime in ISM
        # in this case keep the record that has the most combined runtime
        # because in observed cases of this the extra record has 0 runtime.
        _runtime_sum_column = "sum_runtime"
        _data[_runtime_sum_column] = _data[
            set(self.internal_spec.equipment.spec.keys()) & set(_data.columns)
        ].sum(axis=1)
        # last duplicate datetime value will have maximum sum_runtime
        _data = _data.sort_values(
            [self.internal_spec.datetime_column, _runtime_sum_column],
            ascending=True,
        )
        _data = _data.drop_duplicates(
            subset=[STATES.DATE_TIME], keep="last", ignore_index=True
        )
        _data = _data.drop(columns=[_runtime_sum_column])

        # the period data source is expected at
        _expected_period = f"{self.internal_spec.data_period_seconds}S"

        _min_datetime = _data[self.internal_spec.datetime.datetime_column].min()
        _max_datetime = _data[self.internal_spec.datetime.datetime_column].max()

        # truncate the data to desired simulation start and end time
        _data = _data[
            (_data[self.internal_spec.datetime_column] >= self.sim_config["start_utc"])
            & (_data[self.internal_spec.datetime_column] <= self.sim_config["end_utc"])
        ].reset_index(drop=True)

        # remove unused categories from categorical columns after date range
        # for simulation is selected
        for _cat_col in [
            _col
            for _col in _data.columns
            if isinstance(_data[_col].dtype, pd.api.types.CategoricalDtype)
        ]:
            _data[_cat_col].cat = _data[_cat_col].cat.remove_unused_categories()

        # run settings change point detection before filling missing data
        # the fill data would create false positive change points
        # the change points can also be used to correctly fill the schedule
        # and comfort preferences
        (
            _change_points_schedule,
            _change_points_comfort_prefs,
            _change_points_hvac_mode,
        ) = ThermostatChannel.get_settings_change_points(
            _data, self.internal_spec.data_period_seconds
        )

        # ffill first 15 minutes of missing data periods
        _data = DataClient.fill_missing_data(
            full_data=_data,
            expected_period=_expected_period,
            data_spec=self.internal_spec,
        )
        # compute full_data_periods with only first 15 minutes ffilled
        self.full_data_periods = DataClient.get_full_data_periods(
            full_data=_data,
            data_spec=self.internal_spec,
            expected_period=_expected_period,
            min_sim_period=self.sim_config["min_sim_period"],
        )

        # need time zone before init of DatetimeChannel
        internal_timezone = DateTimeChannel.get_timezone(
            self.sim_config["latitude"], self.sim_config["longitude"]
        )

        # there will be filled data even if there are no full_data_periods
        # the fill data is present to run continuous simulations smoothly
        # in the presence of potentially many missing data periods
        if self.full_data_periods:
            # compute the total sim steps for later use determining offset for
            # weather forecasts idx
            _total_sim_steps = (
                _data[self.internal_spec.datetime_column].max()
                - _data[self.internal_spec.datetime_column].min()
            ) // pd.Timedelta(seconds=self.sim_config["sim_step_size_seconds"])

            # the simulation period must be full days starting at 0 hour to use
            # SimulationControl: Run Simulation for Weather File Run Periods
            _start_utc, _end_utc = self.get_simulation_period(
                expected_period=_expected_period,
                internal_timezone=internal_timezone,
            )

            # add records for warm_up period
            _data = DataClient.add_fill_records(
                df=_data,
                data_spec=self.internal_spec,
                start_utc=_start_utc,
                end_utc=_end_utc,
                expected_period=_expected_period,
            )

            # drop records before and after full simulation time
            # end is less than
            _data = _data[
                (_data[self.internal_spec.datetime_column] >= _start_utc)
                & (_data[self.internal_spec.datetime_column] <= _end_utc)
            ].reset_index(drop=True)

            # bfill to interpolate missing data
            # first and last records must be full because we used full data periods
            # need to add a NA_code to stop fillna from clobbering columns
            # where NA means something
            na_code_name = "NA_code"
            _data[STATES.CALENDAR_EVENT].cat.add_categories(
                new_categories=na_code_name, inplace=True
            )
            _data[STATES.CALENDAR_EVENT] = _data[STATES.CALENDAR_EVENT].fillna(
                na_code_name
            )
            # bfill then ffill to handle where no data after null
            _data = _data.fillna(method="bfill", limit=None)
            _data = _data.fillna(method="ffill", limit=None)

            _data = DataClient.resample_to_step_size(
                df=_data,
                step_size_seconds=self.sim_config["sim_step_size_seconds"],
                data_spec=self.internal_spec,
            )

            # we can replace na_code_name now that filling is complete
            _data.loc[
                _data[STATES.CALENDAR_EVENT] == na_code_name,
                [STATES.CALENDAR_EVENT],
            ] = pd.NA

            # finally convert dtypes to final types now that nulls in
            # non-nullable columns have been properly filled or removed
            _data = convert_spec(
                _data,
                src_spec=self.internal_spec,
                dest_spec=self.internal_spec,
                src_nullable=True,
                dest_nullable=False,
            )

        else:
            raise ValueError(
                f"ID={self.sim_config['identifier']} has no full_data_periods "
                + "for requested duration: "
                + f"start_utc={self.sim_config['start_utc']}, "
                + f"end_utc={self.sim_config['end_utc']} "
                + f"with min_sim_period={self.sim_config['min_sim_period']}. "
                + f"The given data file runs from {_min_datetime}"
                + f" to {_max_datetime}. "
                + f"If there is overlap between these two time periods then "
                + "there is too much missing data. If there is no overlap "
                + "consider altering your sim_config start_utc and end_utc."
            )

        self.datetime = DateTimeChannel(
            data=_data[
                self.internal_spec.intersect_columns(
                    _data.columns, self.internal_spec.datetime.spec
                )
            ],
            spec=self.internal_spec.datetime,
            latitude=self.sim_config["latitude"],
            longitude=self.sim_config["longitude"],
            internal_timezone=internal_timezone,
        )

        # finally create the data channel objs for usage during simulation
        self.thermostat = ThermostatChannel(
            data=_data[
                self.internal_spec.intersect_columns(
                    _data.columns, self.internal_spec.thermostat.spec
                )
            ],
            spec=self.internal_spec.thermostat,
            change_points_schedule=_change_points_schedule,
            change_points_comfort_prefs=_change_points_comfort_prefs,
            change_points_hvac_mode=_change_points_hvac_mode,
        )

        self.equipment = EquipmentChannel(
            data=_data[
                self.internal_spec.intersect_columns(
                    _data.columns, self.internal_spec.equipment.spec
                )
            ],
            spec=self.internal_spec.equipment,
        )

        self.sensors = SensorsChannel(
            data=_data[
                self.internal_spec.intersect_columns(
                    _data.columns, self.internal_spec.sensors.spec
                )
            ],
            spec=self.internal_spec.sensors,
        )
        self.sensors.drop_unused_room_sensors()

        self.weather = WeatherChannel(
            data=_data[
                self.internal_spec.intersect_columns(
                    _data.columns, self.internal_spec.weather.spec
                )
            ],
            spec=self.internal_spec.weather,
            weather_forecast_source=self.weather_forecast_source,
            archive_tmy3_dir=self.archive_tmy3_dir,
            archive_tmy3_data_dir=self.archive_tmy3_data_dir,
            ep_tmy3_cache_dir=self.ep_tmy3_cache_dir,
            nrel_dev_api_key=self.nrel_dev_api_key,
            nrel_dev_email=self.nrel_dev_email,
            nsrdb_cache_dir=self.nsrdb_cache_dir,
            simulation_epw_dir=self.simulation_epw_dir,
        )

        # add nsrdb solar data fields
        self.weather.data = self.weather.fill_nsrdb(
            input_data=self.weather.data,
            datetime_channel=self.datetime,
            sim_config=self.sim_config,
        )

        # merge current weather data with epw
        # backfill of any missing weather data here
        self.weather.get_epw_data(
            sim_config=self.sim_config,
            datetime_channel=self.datetime,
            epw_path=self.epw_path,
        )

        # TODO: this is an example implementation showing
        # the anticapated structure of forecast data from
        # an external source
        self.weather.get_forecast_data(
            sim_config=self.sim_config,
            total_sim_steps=_total_sim_steps,
        )
        # set flag for other simulations using this data client
        self.has_data = True

    def get_simulation_period(self, expected_period, internal_timezone):
        # set start and end times from full_data_periods and simulation config
        # take limiting period as start_utc and end_utc
        if not self.full_data_periods:
            self.start_utc = None
            self.end_utc = None

            return self.start_utc, self.end_utc

        if self.sim_config["start_utc"] >= self.full_data_periods[0][0]:
            self.start_utc = self.sim_config["start_utc"]
        else:
            logger.info(
                f"config start_utc={self.sim_config['start_utc']} is before "
                + f"first full data period={self.full_data_periods[0][0]}. "
                + "Simulation start_utc set to first full data period."
            )
            self.start_utc = self.full_data_periods[0][0]

        if self.sim_config["end_utc"] <= self.full_data_periods[-1][-1]:
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

        # fill additional day before simulation and up end of day end of simulation
        (self.start_utc, self.end_utc,) = DataClient.eplus_day_fill_simulation_time(
            start_utc=self.start_utc,
            end_utc=self.end_utc,
            expected_period=expected_period,
            internal_timezone=internal_timezone,
        )

        return self.start_utc, self.end_utc

    def store_output(self, output, sim_name, src_spec):
        self.destination.put_data(df=output, sim_name=sim_name, src_spec=src_spec)

    def store_input(
        self,
        filepath_or_buffer,
        df_input=None,
        src_spec=None,
        dest_spec=None,
        file_extension=None,
    ):
        """For usage capturing input data for unit tests."""
        if not df_input:
            df_input = self.get_full_input()

        if not src_spec:
            src_spec = self.internal_spec

        if not dest_spec:
            dest_spec = self.destination.data_spec

        if not file_extension:
            file_extension = self.destination.file_extension

        _df = convert_spec(
            df=df_input, src_spec=src_spec, dest_spec=dest_spec, copy=True
        )

        self.destination.write_data_by_extension(
            _df,
            filepath_or_buffer,
            data_spec=dest_spec,
            file_extension=file_extension,
        )

    @staticmethod
    def add_fill_records(df, data_spec, start_utc, end_utc, expected_period):
        if not (start_utc and end_utc):
            return df

        rec = pd.Series(pd.NA, index=df.columns)

        should_resample = False
        if df[(df[data_spec.datetime_column] == start_utc)].empty:
            # append record with start_utc time
            rec[data_spec.datetime_column] = start_utc
            df = df.append(rec, ignore_index=True).sort_values(
                data_spec.datetime_column
            )
            should_resample = True

        if df[(df[data_spec.datetime_column] == end_utc)].empty:
            # append record with end_utc time
            rec[data_spec.datetime_column] = end_utc
            df = df.append(rec, ignore_index=True).sort_values(
                data_spec.datetime_column
            )
            should_resample = True

        if should_resample:
            # frequency rules have different str format
            _str_format_dict = {
                "M": "T",  # covert minutes formats
                "S": "S",
            }
            # replace last char using format conversion dict
            resample_freq = (
                expected_period[0:-1] + _str_format_dict[expected_period[-1]]
            )

            # resampling
            df = df.set_index(data_spec.datetime_column)
            df = df.resample(resample_freq).asfreq()
            df = df.reset_index()

        # adding a null record breaks categorical dtypes
        # convert back to categories
        for state in df.columns:
            if data_spec.full.spec[state]["dtype"] == "category":
                df[state] = df[state].astype("category")

        return df

    @staticmethod
    def eplus_day_fill_simulation_time(
        start_utc, end_utc, expected_period, internal_timezone
    ):
        # EPlus requires that total simulation time be divisible by 86400 seconds
        # or whole days. EPlus also has some transient behaviour at t_init
        # adding time to beginning of simulation input data that will be
        # backfilled is more desirable than adding time to end of simulation
        # this time will not be included in the full_data_periods and thus
        # will not be considered during analysis

        # fill extra day before simulation and up to end of day at end of simulation

        # the added_timedelta is the difference to wholes days minus one period
        # this period can be considered 23:55 to 00:00
        # EnergyPlus will be initialized for this extra period but not simulated

        # date 10 days into year is used for offset because it wont cross DST or
        # year line under any circumstances
        tz_offset_seconds = internal_timezone.utcoffset(
            datetime(start_utc.year, 1, 10)
        ).total_seconds()
        filled_start_utc = start_utc - pd.Timedelta(
            days=1,
            hours=start_utc.hour,
            minutes=start_utc.minute,
            seconds=start_utc.second + tz_offset_seconds,
        )

        filled_end_utc = end_utc

        return filled_start_utc, filled_end_utc

    @staticmethod
    def get_full_data_periods(
        full_data, data_spec, expected_period="300S", min_sim_period="7D"
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
        diffs = full_data.dropna(axis="rows", subset=data_spec.full.null_check_columns)[
            data_spec.datetime_column
        ].diff()

        # seperate periods by missing data
        periods_df = diffs[diffs > pd.to_timedelta(expected_period)].reset_index()

        # make df of periods
        periods_df["start"] = full_data.loc[
            periods_df["index"], data_spec.datetime_column
        ].reset_index(drop=True)

        periods_df["end"] = periods_df["start"] - periods_df[1]

        periods_df = periods_df.drop(axis="columns", columns=["index", 1])

        # append start and end datetimes from full_data
        periods_df.loc[len(periods_df)] = [
            pd.NA,
            full_data.loc[len(full_data) - 1, data_spec.datetime_column],
        ]
        periods_df["start"] = periods_df["start"].shift(1)
        periods_df.loc[0, "start"] = full_data.loc[0, data_spec.datetime_column]

        # only include full_data_periods that are geq min_sim_period
        # convert all np.arrays to lists for ease of use
        _full_data_periods = [
            list(rec)
            for rec in periods_df[
                periods_df["end"] - periods_df["start"] >= pd.Timedelta(min_sim_period)
            ].to_numpy()
        ]

        return _full_data_periods

    @staticmethod
    def fill_missing_data(
        full_data,
        data_spec,
        expected_period,
        limit=3,
        method="ffill",
    ):
        """Fill periods of missing data within limit using method.
        Periods larger than limit will not be partially filled."""
        if full_data.empty:
            return full_data

        # frequency rules have different str format
        _str_format_dict = {
            "M": "T",  # covert minutes formats
            "S": "S",
        }
        # replace last char using format conversion dict
        resample_freq = expected_period[0:-1] + _str_format_dict[expected_period[-1]]
        # resample to add any timesteps that are fully missing
        full_data = full_data.set_index(data_spec.datetime_column)
        full_data = full_data.resample(resample_freq).asfreq()
        full_data = full_data.reset_index()

        # compute timesteps between steps of data
        _null_check_columns = [
            _col
            for _col in data_spec.full.null_check_columns
            if _col in full_data.columns
        ]
        diffs = full_data.dropna(axis="rows", subset=_null_check_columns)[
            data_spec.datetime_column
        ].diff()

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
                fill_idxs = fill_idxs + [i for i in range(idx - (num_missing), idx + 1)]

            # fill exact idxs that are missing using method
            full_data.iloc[fill_idxs] = full_data.iloc[fill_idxs].fillna(method=method)

        return full_data

    def get_full_input(self, column_names=False):
        full_input = pd.concat(
            [
                self.datetime.data,
                self.thermostat.data,
                self.equipment.data,
                self.sensors.data,
                self.weather.data,
            ],
            axis="columns",
        )
        # drop duplicated datetime columns
        full_input = full_input.loc[:, ~full_input.columns.duplicated()]

        # remove warm up time and forecast time
        full_input = full_input[
            (
                full_input[self.internal_spec.datetime_column]
                >= self.sim_config["start_utc"]
            )
            & (
                full_input[self.internal_spec.datetime_column]
                < self.sim_config["end_utc"]
            )
        ].reset_index(drop=True)

        # resample to output step size
        full_input = DataClient.resample_to_step_size(
            df=full_input,
            step_size_seconds=self.sim_config["output_step_size_seconds"],
            data_spec=self.internal_spec,
        )

        if column_names:
            full_input.columns = [
                self.internal_spec.full.spec[_col]["name"]
                for _col in full_input.columns
            ]

        return full_input

    @staticmethod
    def resample_to_step_size(df, step_size_seconds, data_spec):
        """This function contains the rules for resampling data of all
        types different time steps"""
        # the mode seconds between messages is the expected sample period
        cur_sample_period = (
            df[data_spec.datetime_column].diff().mode()[0].total_seconds()
        )

        if cur_sample_period < step_size_seconds:
            # downsample data to lower frequency
            df = DataClient.downsample_to_step_size(df, step_size_seconds, data_spec)
        elif cur_sample_period > step_size_seconds:
            # upsample data to higher frequency
            df = DataClient.upsample_to_step_size(df, step_size_seconds, data_spec)

        return df

    @staticmethod
    def upsample_to_step_size(df, step_size_seconds, data_spec):
        """This function contains the rules for resampling data of all
        types into smaller time steps"""
        # resample to desired frequency
        _resample_period = f"{step_size_seconds}S"
        current_step_size = int(
            df[data_spec.datetime_column].diff().mode()[0].total_seconds()
        )

        # runtime_columns can be filled with zeros because they are not used
        runtime_columns = [
            _state
            for _state, _v in data_spec.full.spec.items()
            if ((_v["unit"] == UNITS.SECONDS) and (_state in df.columns))
        ]

        # before resampling generate step_end_on column for runtime columns
        # we must know if the end of the step cycle is one or off
        for _col in runtime_columns:
            # TODO: define min cycle time for all equipment
            min_cycle_time = 300
            df[f"{_col}_step_end_off"] = (
                (
                    ((df[_col] + df[_col].shift(1)) >= min_cycle_time)
                    & ((df[_col] + df[_col].shift(-1)) <= min_cycle_time)
                )
                & ~(
                    ((df[_col].shift(1) + df[_col].shift(2)) >= min_cycle_time)
                    & ((df[_col] + df[_col].shift(1)) <= min_cycle_time)
                )
                | ((df[_col] + df[_col].shift(-1)) < min_cycle_time)
            ).astype("boolean")

        # we need to set a datetime index to resample
        df = df.set_index(data_spec.datetime_column)
        df = df.resample(_resample_period).asfreq()
        # the datetime index can be reset back to a column
        # this is actually required due to an issue in the interpolate method
        df = df.reset_index()

        # linear interpolation
        # setpoint columns which are in units that can be interpolated,
        # must not be interpolated, but ffilled, exclude them from list
        linear_columns_exclude = [
            STATES.TEMPERATURE_STP_COOL,
            STATES.TEMPERATURE_STP_HEAT,
            STATES.HUMIDITY_EXPECTED_LOW,
            STATES.HUMIDITY_EXPECTED_HIGH,
        ]
        linear_columns = [
            _state
            for _state, _v in data_spec.full.spec.items()
            if (
                (_v["unit"] in [UNITS.CELSIUS, UNITS.RELATIVE_HUMIDITY])
                and (_state in df.columns)
            )
            and (_state not in linear_columns_exclude)
        ]
        # Note: must have numpy `float32` or `float64` dtypes for interpolation
        df.loc[:, linear_columns] = df.loc[:, linear_columns].interpolate(
            axis="rows", method="linear"
        )

        # ffill interpolation
        ffill_columns = [
            _state
            for _state, _v in data_spec.full.spec.items()
            if ((_v["unit"] == UNITS.OTHER) and (_state in df.columns))
        ]
        ffill_columns = ffill_columns + list(
            set(linear_columns_exclude) & set(df.columns)
        )
        df.loc[:, ffill_columns] = df.loc[:, ffill_columns].interpolate(
            axis="rows", method="ffill"
        )

        # run time columns must be disaggregated using minimum runtime
        # rules to determin if runtime happens in beginning or end of step
        # step idx used to determin leftover runtime
        upsample_ratio = int(current_step_size / step_size_seconds)
        df["inner_step_idx"] = np.hstack(
            (
                [upsample_ratio],
                np.tile(
                    np.arange(1, upsample_ratio + 1),
                    (int((len(df) - 1) / upsample_ratio), 1),
                ).flatten(),
            )
        )
        for _col in runtime_columns:
            df[f"{_col}_step_end_off"] = df[f"{_col}_step_end_off"].bfill()

            # runtime sum over step
            df["step_runtime"] = df[_col].shift(-upsample_ratio).ffill().shift(1)

            # runtime at beginning of step
            df["b_upsample"] = df["step_runtime"] - (
                (df["inner_step_idx"] - 1) * step_size_seconds
            )
            df.loc[
                df["b_upsample"] > step_size_seconds, ["b_upsample"]
            ] = step_size_seconds

            # runtime at end of step
            df["e_upsample"] = df["step_runtime"] - (
                (upsample_ratio - df["inner_step_idx"]) * step_size_seconds
            )
            df.loc[
                df["e_upsample"] > step_size_seconds, ["e_upsample"]
            ] = step_size_seconds

            # steps ending with off-cycle
            df.loc[df[f"{_col}_step_end_off"], [_col]] = df["b_upsample"]
            df.loc[~df[f"{_col}_step_end_off"], [_col]] = df["e_upsample"]
            df.loc[df[_col] < 0, [_col]] = 0
            df[_col] = df[_col].fillna(0)

            df = df.drop(columns=[f"{_col}_step_end_off"])

        df = df.drop(
            columns=["e_upsample", "b_upsample", "step_runtime", "inner_step_idx"]
        )

        # as inputs and will just be re-aggregated into output
        zero_fill_columns = [
            _state
            for _state, _v in data_spec.full.spec.items()
            if ((_v["unit"] == UNITS.SECONDS) and (_state in df.columns))
        ]
        df.loc[:, zero_fill_columns] = df.loc[:, zero_fill_columns].fillna(0)

        return df

    @staticmethod
    def downsample_to_step_size(df, step_size_seconds, data_spec):
        """This function contains the rules for integrating data of all
        types into larger time steps"""

        # resample to desired frequency
        _resample_period = f"{step_size_seconds}S"
        # we need to set a datetime index to resample
        df = df.set_index(data_spec.datetime_column)

        # set result df with new frequency
        # each group of columns must be filled in separately
        res_df = df.resample(_resample_period).asfreq()

        # mean integration
        mean_columns = [
            _state
            for _state, _v in data_spec.full.spec.items()
            if (
                _v["unit"] in [UNITS.CELSIUS, UNITS.RELATIVE_HUMIDITY]
                and _state in df.columns
            )
        ]
        res_df.loc[:, mean_columns] = (
            df.loc[:, mean_columns].resample(_resample_period).mean()
        )

        # mode interpolation
        # columns that were ffilled and represent current states will
        # be filled with the most recent value as the default resample().asfreq()

        # sum integration
        sum_columns = [
            _state
            for _state, _v in data_spec.full.spec.items()
            if (_v["unit"] == UNITS.SECONDS and _state in df.columns)
        ]
        res_df.loc[:, sum_columns] = (
            df.loc[:, sum_columns].resample(_resample_period).sum()
        )

        # the datetime index can be reset back to a column
        res_df = res_df.reset_index()
        return res_df

    @staticmethod
    def generate_dummy_data(
        sim_config,
        spec,
        outdoor_weather=None,
        schedule_chg_pts=None,
        comfort_chg_pts=None,
        hvac_mode_chg_pts=None,
    ):
        if isinstance(spec, Internal):
            raise ValueError(
                f"Supplied Spec {spec} is internal spec."
                + " Data of this spec should not be stored in data files"
            )

        for _idx, sim in sim_config.iterrows():
            # _df = pd.DataFrame(columns=spec.full.spec.keys())
            _df = pd.DataFrame(
                index=pd.date_range(
                    start=sim.start_utc,
                    end=sim.end_utc,
                    freq=f"{spec.data_period_seconds}S",
                )
            )

            if not schedule_chg_pts:
                # set default ecobee schedule
                schedule_chg_pts = {
                    sim.start_utc: [
                        {
                            "name": "Home",
                            "minute_of_day": 390,
                            "on_day_of_week": [
                                True,
                                True,
                                True,
                                True,
                                True,
                                True,
                                True,
                            ],
                        },
                        {
                            "name": "Sleep",
                            "minute_of_day": 1410,
                            "on_day_of_week": [
                                True,
                                True,
                                True,
                                True,
                                True,
                                True,
                                True,
                            ],
                        },
                    ]
                }

            if not comfort_chg_pts:
                # set default ecobee comfort setpoints
                if isinstance(spec, FlatFilesSpec):
                    home_stp_cool = Conversions.C2Fx10(23.5)
                    home_stp_heat = Conversions.C2Fx10(21.0)
                    sleep_stp_cool = Conversions.C2Fx10(28.0)
                    sleep_stp_heat = Conversions.C2Fx10(16.5)
                elif isinstance(spec, DonateYourDataSpec):
                    home_stp_cool = Conversions.C2F(23.5)
                    home_stp_heat = Conversions.C2F(21.0)
                    sleep_stp_cool = Conversions.C2F(28.0)
                    sleep_stp_heat = Conversions.C2F(16.5)
                else:
                    home_stp_cool = 23.5
                    home_stp_heat = 21.0
                    sleep_stp_cool = 28.0
                    sleep_stp_heat = 16.5

                comfort_chg_pts = {
                    sim.start_utc: {
                        "Home": {
                            STATES.TEMPERATURE_STP_COOL: home_stp_cool,
                            STATES.TEMPERATURE_STP_HEAT: home_stp_heat,
                        },
                        "Sleep": {
                            STATES.TEMPERATURE_STP_COOL: sleep_stp_cool,
                            STATES.TEMPERATURE_STP_HEAT: sleep_stp_heat,
                        },
                    }
                }

            if not hvac_mode_chg_pts:
                # set default ecobee comfort setpoints
                hvac_mode_chg_pts = {sim.start_utc: "heat"}

            # enforce ascending sorting of dict keys
            hvac_mode_chg_pts = dict(sorted(hvac_mode_chg_pts.items()))
            comfort_chg_pts = dict(sorted(comfort_chg_pts.items()))
            schedule_chg_pts = dict(sorted(schedule_chg_pts.items()))

            # check for errors in settings
            if len(hvac_mode_chg_pts) <= 0:
                raise ValueError(f"Invalid hvac_mode_chg_pts={hvac_mode_chg_pts}.")
            if len(comfort_chg_pts) <= 0:
                raise ValueError(f"Invalid comfort_chg_pts={comfort_chg_pts}.")
            if len(schedule_chg_pts) <= 0:
                raise ValueError(f"Invalid schedule_chg_pts={schedule_chg_pts}.")

            for k, v in spec.full.spec.items():
                _default_value, _ = Conversions.numpy_down_cast_default_value_dtype(
                    v["dtype"]
                )
                if v["channel"] == CHANNELS.THERMOSTAT_SETTING:
                    # settings channels set with default values first
                    # they are set below after full df columns have been filled
                    _df[k] = _default_value
                elif v["channel"] == CHANNELS.WEATHER:
                    # default: set no values for outdoor_weather=None
                    # will default to using TMY3 data for the provided location
                    if outdoor_weather:
                        # outdoor_weather can be set with internal states as keys
                        if v["internal_state"] in outdoor_weather.keys():
                            _df[k] = outdoor_weather[v["internal_state"]]

                elif v["channel"] == CHANNELS.THERMOSTAT_SENSOR:
                    # sensor data unused for dummy data
                    # set default
                    _df[k] = _default_value
                elif v["channel"] == CHANNELS.EQUIPMENT:
                    # equipment data unused for dummy data
                    # set default
                    _df[k] = _default_value

            # settings is always in spec add in specific order
            # 1. add HVAC_MODE
            k_hvac_mode = [
                k
                for k, v in spec.full.spec.items()
                if v["internal_state"] == STATES.HVAC_MODE
            ][0]
            # assuming sorted ascending by timestamp
            # each change point sets all future hvac modes
            for _ts, _hvac_mode in hvac_mode_chg_pts.items():
                _df.loc[_df.index >= _ts, k_hvac_mode] = _hvac_mode

            # 2. add SCHEDULE
            k_schedule = [
                k
                for k, v in spec.full.spec.items()
                if v["internal_state"] == STATES.SCHEDULE
            ][0]
            # assuming sorted ascending by timestamp
            # each change point sets all future schedules
            for _ts, _schedule in schedule_chg_pts.items():
                for _dow in range(7):
                    _dow_schedule = [
                        _s for _s in _schedule if _s["on_day_of_week"][_dow]
                    ]
                    _dow_schedule = sorted(
                        _dow_schedule, key=lambda k: k["minute_of_day"]
                    )
                    _prev_dow_schedule = [
                        _s for _s in _schedule if _s["on_day_of_week"][(_dow - 1) % 7]
                    ]
                    _prev_dow_schedule = sorted(
                        _prev_dow_schedule, key=lambda k: k["minute_of_day"]
                    )
                    # first period is defined from previous day of week last schedule
                    _prev_s = _prev_dow_schedule[-1]
                    _s = _dow_schedule[0]
                    _df.loc[
                        (_df.index >= _ts)
                        & (_df.index.day_of_week == _dow)
                        & (
                            _df.index.hour * 60 + _df.index.minute < _s["minute_of_day"]
                        ),
                        k_schedule,
                    ] = _prev_s["name"]
                    for _s in _dow_schedule:

                        _df.loc[
                            (_df.index >= _ts)
                            & (_df.index.day_of_week == _dow)
                            & (
                                _df.index.hour * 60 + _df.index.minute
                                >= _s["minute_of_day"]
                            ),
                            k_schedule,
                        ] = _s["name"]

            # 3. add SCHEDULE
            k_stp_cool = [
                k
                for k, v in spec.full.spec.items()
                if v["internal_state"] == STATES.TEMPERATURE_STP_COOL
            ][0]
            k_stp_heat = [
                k
                for k, v in spec.full.spec.items()
                if v["internal_state"] == STATES.TEMPERATURE_STP_HEAT
            ][0]
            # assuming sorted ascending by timestamp
            # each change point sets all future comfort set points
            for _ts, _comfort in comfort_chg_pts.items():
                for _schedule_name, _setpoints in _comfort.items():
                    _df.loc[
                        (_df.index >= _ts) & (_df[k_schedule] == _schedule_name),
                        k_stp_cool,
                    ] = _setpoints[STATES.TEMPERATURE_STP_COOL]
                    _df.loc[
                        (_df.index >= _ts) & (_df[k_schedule] == _schedule_name),
                        k_stp_heat,
                    ] = _setpoints[STATES.TEMPERATURE_STP_HEAT]

            _df = _df.reset_index().rename(columns={"index": spec.datetime_column})

            return _df
