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
from BuildingControlsSimulator.DataClients.DataSpec import (
    Internal,
    convert_spec,
)
from BuildingControlsSimulator.DataClients.DateTimeChannel import (
    DateTimeChannel,
)
from BuildingControlsSimulator.DataClients.ThermostatChannel import (
    ThermostatChannel,
)
from BuildingControlsSimulator.DataClients.EquipmentChannel import (
    EquipmentChannel,
)
from BuildingControlsSimulator.DataClients.SensorsChannel import SensorsChannel
from BuildingControlsSimulator.DataClients.WeatherChannel import WeatherChannel
from BuildingControlsSimulator.DataClients.DataSource import DataSource
from BuildingControlsSimulator.DataClients.DataDestination import (
    DataDestination,
)


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
    destination = attr.ib(
        validator=attr.validators.instance_of(DataDestination)
    )
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
    start_utc = attr.ib(default=None)
    end_utc = attr.ib(default=None)
    eplus_fill_to_day_seconds = attr.ib(default=None)
    eplus_warmup_seconds = attr.ib(default=None)
    internal_spec = attr.ib(factory=Internal)

    def __attrs_post_init__(self):
        # first, post init class specification
        self.make_data_directories()

    def make_data_directories(self):
        os.makedirs(self.weather_dir, exist_ok=True)
        os.makedirs(self.archive_tmy3_data_dir, exist_ok=True)
        os.makedirs(self.ep_tmy3_cache_dir, exist_ok=True)
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
        # check for invalid start/end combination
        if self.sim_config["end_utc"] <= self.sim_config["start_utc"]:
            raise ValueError(
                "sim_config contains invalid start_utc >= end_utc."
            )
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

        # truncate the data to desired simulation start and end time
        _data = _data[
            (
                _data[self.internal_spec.datetime_column]
                >= self.sim_config["start_utc"]
            )
            & (
                _data[self.internal_spec.datetime_column]
                <= self.sim_config["end_utc"]
            )
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

        _expected_period = f"{self.internal_spec.data_period_seconds}S"
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
            # the simulation period must be full days starting at 0 hour to use
            # SimulationControl: Run Simulation for Weather File Run Periods
            _start_utc, _end_utc = self.get_simulation_period(
                expected_period=_expected_period,
                internal_timezone=internal_timezone,
            )

            # add records for warmup period
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

        else:
            raise ValueError(
                f"ID={self.sim_config['identifier']} has no full_data_periods "
                + "for requested duration: "
                + f"start_utc={self.sim_config['start_utc']}, "
                + f"end_utc={self.sim_config['end_utc']} "
                + f"with min_sim_period={self.sim_config['min_sim_period']}"
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
            archive_tmy3_dir=self.archive_tmy3_dir,
            archive_tmy3_data_dir=self.archive_tmy3_data_dir,
            ep_tmy3_cache_dir=self.ep_tmy3_cache_dir,
            simulation_epw_dir=self.simulation_epw_dir,
        )

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
        (
            self.start_utc,
            self.end_utc,
        ) = DataClient.eplus_day_fill_simulation_time(
            start_utc=self.start_utc,
            end_utc=self.end_utc,
            expected_period=expected_period,
            internal_timezone=internal_timezone,
        )

        return self.start_utc, self.end_utc

    def store_output(self, output, sim_name, src_spec):
        self.destination.put_data(
            df=output, sim_name=sim_name, src_spec=src_spec
        )

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
        diffs = full_data.dropna(
            axis="rows", subset=data_spec.full.null_check_columns
        )[data_spec.datetime_column].diff()

        # seperate periods by missing data
        periods_df = diffs[
            diffs > pd.to_timedelta(expected_period)
        ].reset_index()

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
        periods_df.loc[0, "start"] = full_data.loc[
            0, data_spec.datetime_column
        ]

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
        resample_freq = (
            expected_period[0:-1] + _str_format_dict[expected_period[-1]]
        )
        # resample to add any timesteps that are fully missing
        full_data = full_data.set_index(data_spec.datetime_column)
        full_data = full_data.resample(resample_freq).asfreq()
        full_data = full_data.reset_index()

        # compute timesteps between steps of data
        diffs = full_data.dropna(
            axis="rows", subset=data_spec.full.null_check_columns
        )[data_spec.datetime_column].diff()

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
            df = DataClient.downsample_to_step_size(
                df, step_size_seconds, data_spec
            )
        elif cur_sample_period > step_size_seconds:
            # upsample data to higher frequency
            df = DataClient.upsample_to_step_size(
                df, step_size_seconds, data_spec
            )

        return df

    @staticmethod
    def upsample_to_step_size(df, step_size_seconds, data_spec):
        """This function contains the rules for resampling data of all
        types into smaller time steps"""
        # resample to desired frequency
        _resample_period = f"{step_size_seconds}S"
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

        # runtime_columns can be filled with zeros because they are not used
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
