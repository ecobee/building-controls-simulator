# created by Tom Stesco tom.s@ecobee.com

import os
import logging
import re
from datetime import datetime
import math
import copy

import pandas as pd
import numpy as np
import attr
import requests
from sklearn.metrics.pairwise import haversine_distances

from BuildingControlsSimulator.DataClients.DataStates import STATES
from BuildingControlsSimulator.DataClients.DataSpec import EnergyPlusWeather
from BuildingControlsSimulator.DataClients.DataChannel import DataChannel
from BuildingControlsSimulator.Conversions.Conversions import Conversions

import h5pyd
from scipy.spatial import cKDTree


logger = logging.getLogger(__name__)


@attr.s(kw_only=True)
class WeatherChannel(DataChannel):
    """Client for weather data."""

    epw_path = attr.ib(default=None)
    epw_data = attr.ib(factory=dict)
    epw_meta = attr.ib(factory=dict)
    fill_epw_data = attr.ib(default=None)
    epw_step_size_seconds = attr.ib(default=None)

    # env variables
    ep_tmy3_cache_dir = attr.ib()
    simulation_epw_dir = attr.ib()
    nrel_dev_api_key = attr.ib(default=None)
    nrel_dev_email = attr.ib(default=None)
    archive_tmy3_dir = attr.ib(default=None)
    archive_tmy3_meta = attr.ib(default=None)
    archive_tmy3_data_dir = attr.ib(default=None)

    # column names
    datetime_column = attr.ib(default=EnergyPlusWeather.datetime_column)
    epw_columns = attr.ib(default=EnergyPlusWeather.epw_columns)
    epw_meta_keys = attr.ib(default=EnergyPlusWeather.epw_meta)
    epw_column_map = attr.ib(default=EnergyPlusWeather.output_rename_dict)

    epw_backfill_columns = attr.ib()

    #QUESTION could this be used for backfilling missing temp and rh?
    @epw_backfill_columns.default
    def get_epw_backfill_columns(self):
        return [STATES.DIRECT_NORMAL_RADIATION, STATES.GLOBAL_HORIZONTAL_RADIATION]

    def make_epw_file(
        self,
        sim_config,
        datetime_channel,
        fill_epw_path=None,
        epw_step_size_seconds=None,
    ):
        """get/open nsrdb file"""
        #TODO:  I could add checks here, but its already done within the method
        fill_nsrdb_path, fill_nsrdb_data = self.get_nsrdb(
            sim_config["latitude"], sim_config["longitude"]
        )

        """Generate epw file in local time"""
        if fill_epw_path:
            if os.path.exists(fill_epw_path):
                fill_epw_fname = os.path.basename(fill_epw_path)
            else:
                ValueError(f"fill_epw_path: {fill_epw_path} does not exist.")
        else:
            # attempt to get .epw data from NREL
            fill_epw_path, fill_epw_fname = self.get_tmy_fill_epw(
                sim_config["latitude"], sim_config["longitude"]
            )

        if epw_step_size_seconds:
            self.epw_step_size_seconds = epw_step_size_seconds
        else:
            self.epw_step_size_seconds = sim_config["sim_step_size_seconds"]

        (fill_epw_data, self.epw_meta, meta_lines,) = self.read_epw(
            fill_epw_path,
        )

        # infer if the years in the epw file are garbage from TMY
        # TMY data is only valid for a period of 1 year and then it must
        # be wrapped to next year if required for multi-year weather data
        # the year supplied in TMY data is not a valid sequential time
        # Therefore the year must be overwritten to desired year
        if len(fill_epw_data["year"].unique()) > 2 and (
            len(fill_epw_data["year"]) < 8762
        ):
            # it is not possible to have full consequtive data for 3 different
            # years and less than 8762 total data points.

            # using the mode will handle the case of shifting data points into
            # adjacent years
            force_year = (
                datetime_channel.data[datetime_channel.spec.datetime_column]
                .dt.year.mode()
                .values[0]
            )
            fill_epw_data = self.convert_epw_to_internal(
                fill_epw_data,
                force_year=force_year,
            )

        # lat/lon time zone is the time zone we localize with
        # the datetime_channel timezone is free to be changed later
        # self.time_zone = copy.deepcopy(datetime_channel.timezone)
        # if self.time_zone:
        _hour_offset = (
            datetime_channel.timezone.utcoffset(datetime.utcnow()).total_seconds()
            / 3600
        )
        if self.epw_meta["TZ"] != _hour_offset:
            logger.warn(
                "Timezones from longitude and latitude and given epw do not match."
            )
            self.epw_meta["TZ"] = _hour_offset

        _epw_path = None
        if not fill_epw_data.empty:
            _epw_path = os.path.join(
                self.simulation_epw_dir,
                "NREL_EPLUS" + f"_{sim_config['identifier']}" + f"_{fill_epw_fname}",
            )

            # add nsrdb solar fields
            # need to pass in original dyd datetime column name
            if not fill_nsrdb_data.empty:
                nsrdb_data = self.fill_nsrdb(
                    input_epw_data=self.data,
                    datetime_channel=datetime_channel,
                    fill_nsrdb_data=fill_nsrdb_data,
                    sim_config=sim_config,
                )
                # follows from fill_nsrdb step
                # fill any missing fields in epw
                # need to pass in original dyd datetime column name
                epw_data = self.fill_epw(
                    input_epw_data=self.data,
                    datetime_channel=datetime_channel,
                    fill_epw_data=fill_epw_data,
                    sim_config=sim_config,
                )
            else:
                logger.error("failed to retrieve .epw fill data.")
                # fill any missing fields in epw
                # need to pass in original dyd datetime column name
                epw_data = self.fill_epw(
                    input_epw_data=self.data,
                    datetime_channel=datetime_channel,
                    fill_epw_data=fill_epw_data,
                    sim_config=sim_config,
                )

            meta_lines = self.add_epw_data_periods(
                epw_data=epw_data,
                meta_lines=meta_lines,
                sim_config=sim_config,
            )

            # save to file
            self.to_epw(
                epw_data=epw_data,
                meta_lines=meta_lines,
                fpath=_epw_path,
            )

            self.epw_path = _epw_path
        else:
            logger.error("failed to retrieve .epw fill data.")

        return self.epw_path

    def add_epw_data_periods(self, epw_data, meta_lines, sim_config):
        # add correct DATA PERIODS reference to metalines
        # see https://bigladdersoftware.com/epx/docs/9-4/auxiliary-programs/energyplus-weather-file-epw-data-dictionary.html
        _starting_timestamp = min(epw_data[self.datetime_column])
        _ending_timestamp = max(epw_data[self.datetime_column])

        # these are the fields required in DATA PERIODS
        _num_data_periods = 1
        _records_per_hour = int(3600 / self.epw_step_size_seconds)
        _data_period_name = "data"
        _start_day_of_week = _starting_timestamp.day_name()
        _start_day = f"{_starting_timestamp.month}/{_starting_timestamp.day}/{_starting_timestamp.year}"
        _end_day = f"{_ending_timestamp.month}/{_ending_timestamp.day}/{_ending_timestamp.year}"

        data_periods_idx = None
        for idx, _line in enumerate(meta_lines):
            if _line.startswith("DATA PERIODS"):
                data_periods_idx = idx

        data_periods_line = "DATA PERIODS,"
        data_periods_line += f"{_num_data_periods},{_records_per_hour},"
        data_periods_line += f"{_data_period_name},{_start_day_of_week},"
        data_periods_line += f"{_start_day},{_end_day}"
        data_periods_line += "\n"

        if data_periods_idx:
            meta_lines[data_periods_idx] = data_periods_line
        else:
            meta_lines.append(data_periods_line)

        return meta_lines

    def read_epw(self, fpath):
        """
        Given a file-like buffer with data in Energy Plus Weather (EPW) format,
        parse the data into a dataframe.

        EPW data is composed of data from different years.
        EPW files always have 365*24 = 8760 data rows
        be careful with the use of leap years.
        Parameters
        ----------
        csvdata : file-like buffer
            a file-like buffer containing data in the EPW format

        Returns
        -------
        data : DataFrame
            A pandas dataframe with the columns described in the table
            below. For more detailed descriptions of each component, please
            consult the EnergyPlus Auxiliary Programs documentation
            available at: https://energyplus.net/documentation.
        meta : dict
            The site metadata available in the file.
        meta_epw_lines : list
            All lines of meta data.
        See Also
        --------
        pvlib.iotools.read_epw
        """
        # read meta data into list of lines, determine n_meta_line
        # the last meta data line is marked with "DATA PERIODS"
        meta_epw_lines = []
        with open(fpath, "r") as f:
            for n_meta_line in range(10):
                meta_epw_lines.append(f.readline())
                if meta_epw_lines[n_meta_line].split(",")[0] == "DATA PERIODS":
                    break

        meta = dict(zip(self.epw_meta_keys, meta_epw_lines[0].rstrip("\n").split(",")))
        meta["altitude"] = float(meta["altitude"])
        meta["latitude"] = float(meta["latitude"])
        meta["longitude"] = float(meta["longitude"])
        meta["TZ"] = float(meta["TZ"])

        # use starting line determined above
        data = pd.read_csv(
            fpath, skiprows=n_meta_line, header=0, names=self.epw_columns
        )

        data = data.astype(
            {
                "year": "Int16",
                "month": "Int8",
                "day": "Int8",
                "hour": "Int8",
                "minute": "Int8",
            },
        )

        return data, meta, meta_epw_lines

    def convert_epw_to_internal(self, data, use_datetime=True, force_year=None):
        # some EPW files have minutes=60 to represent the end of the hour
        # this doesnt actually mean it is the next hour, it should be 0
        # see: https://discourse.radiance-online.org/t/ \
        # meaning-of-epw-files-minute-field-and-why-is-it-60-in-tmy2- \
        # based-epw-and-0-in-tmy3-based-epw/1462/3
        if data["minute"].mean() == 60:
            data["minute"] = 0

        # EPW format uses hour = [1-24], set to [0-23]
        data["hour"] = data["hour"] - 1

        if force_year:
            data["year"] = int(force_year)

        # create datetime column in UTC
        data[self.datetime_column] = pd.to_datetime(
            data[["year", "month", "day", "hour", "minute"]]
            .astype(int)
            .astype(str)
            .apply("-".join, 1),
            format="%Y-%m-%d-%H-%M",
        )

        # localize and convert to UTC
        data[self.datetime_column] = (
            data[self.datetime_column]
            .dt.tz_localize(int(self.epw_meta["TZ"] * 3600))
            .dt.tz_convert(tz="UTC")
        )

        # reset year, month, day, hour, minute columns
        # the year must be forced back to wrap the year after TZ shift
        data["year"] = force_year
        data["month"] = data[self.datetime_column].dt.month
        data["day"] = data[self.datetime_column].dt.day
        data["hour"] = data[self.datetime_column].dt.hour
        data["minute"] = data[self.datetime_column].dt.minute

        data = data.sort_values(
            ["year", "month", "day", "hour", "minute"], ascending=True
        )

        if not use_datetime:
            data = data.drop(axis="columns", columns=[self.datetime_column])

        return data

    def get_cdo(self):
        raise NotImplementedError
        # TODO:
        # https://www.ncdc.noaa.gov/cdo-web/webservices/v2#gettingStarted
        pass

    def get_psm(self, location):
        raise NotImplementedError
        # TODO:
        # url = (
        #     "https://developer.nrel.gov/api/nsrdb/v2/solar/psm3-tmy-download.csv"
        #     + f"?wkt=POINT({lon}%20{lat})&names={year}&leap_day={leap_year}"
        #     + f"&api_key={self.nrel_dev_api_key}&attributes={attributes}"
        #     + f"&utc={utc}&full_name={name}&email={email}&interval={interval}"
        # )
        pass

    def get_tmy_fill_epw(self, lat, lon):

        eplus_github_weather_geojson_url = "https://raw.githubusercontent.com/NREL/EnergyPlus/develop/weather/master.geojson"

        # check for cached eplus geojson
        # cache is updated daily
        cache_name = f"eplus_geojson_cache_{datetime.today().strftime('%Y_%m_%d')}.csv"
        if self.archive_tmy3_dir:
            cache_path = os.path.join(self.archive_tmy3_dir, cache_name)
        if self.archive_tmy3_dir and os.path.exists(cache_path):
            logger.info(f"Reading TMY weather geojson from cache: {cache_path}")
            df = pd.read_csv(cache_path)
            if df.empty:
                logger.error("Cached TMY weather geojson is empty.")
        else:
            logger.info(
                f"Downloading TMY weather geojson from: {eplus_github_weather_geojson_url}"
            )
            df = pd.json_normalize(
                pd.read_json(eplus_github_weather_geojson_url).features
            )
            # parse coordinates column to lat lon in radians for usage
            # the geojson coordinates are [lon, lat]
            coordinates_col = "geometry.coordinates"
            df[["lon", "lat"]] = pd.DataFrame(
                df[coordinates_col].to_list(), columns=["lon", "lat"]
            )
            df = df.drop(axis="columns", columns=[coordinates_col])
            df["lat"] = np.radians(df["lat"])
            df["lon"] = np.radians(df["lon"])

        if self.archive_tmy3_dir and os.path.isdir(self.archive_tmy3_dir):
            df.to_csv(cache_path, index=False)

        # convert query point to radians and set dimensionality to (2,1)
        qp = np.radians(np.atleast_2d(np.array([lat, lon])))
        dis = haversine_distances(df[["lat", "lon"]].values, qp)

        # TODO: add finding of TMY3 datasets over TMY of same/similar location
        # e.g. for phoenix this method find TMY data while TMY3 data exists but
        # has different coordinates
        epw_href = df.iloc[np.argmin(dis)]["properties.epw"]

        # extract download URL from html link
        match = re.search(r'href=[\'"]?([^\'" >]+)', epw_href)

        fpath = None
        if match:
            epw_url = match.group(1)
            fname = epw_url.split("/")[-1]
            if fname:
                fpath = os.path.join(self.ep_tmy3_cache_dir, fname)
                # if already downloaded return name and path to cache
                if not os.path.exists(fpath):
                    logger.info(f"Downloading TMY weather data from: {epw_url}")
                    res = requests.get(epw_url, allow_redirects=True)
                    if res.status_code == 200:
                        with open(fpath, "wb") as f:
                            f.write(res.content)

        return fpath, fname

    def get_archive_tmy3(self, lat, lon):
        """Retrieve TMY3 data from archive based on minimum haversine distance.
        This requries downloading archive.

        See README.md section on NSRDB 1991-2005 Archive Data:

        The archived data contains the most recent TMY3 data with the fields
        required by the EPW format. Download the archive from:
        https://nsrdb.nrel.gov/data-sets/archives.html

        Note: The archive is ~3 GB, but only the TMY data
        (~300MB compressed, 1.7 GB uncompressed) is required and
        the hourly data can be deleted after download.

        :param lat: latitude
        :type lat: float
        :param lon: longitude
        :type lon: float
        :return: TMY3 data
        :rtype: pd.DataFrame
        """
        # only need these columns
        tmy3_meta = pd.read_csv(
            self.archive_tmy3_meta, usecols=["USAF", "Latitude", "Longitude"]
        )

        # convert query point and all stations all to radians
        qp = np.radians(np.atleast_2d(np.array([lat, lon])))
        tmy3_meta["Latitude"] = np.radians(tmy3_meta["Latitude"])
        tmy3_meta["Longitude"] = np.radians(tmy3_meta["Longitude"])

        # compute haversine distance from all stations to query point
        dis = haversine_distances(tmy3_meta[["Latitude", "Longitude"]].values, qp)

        # station that minimizes distance from query point should be used
        usaf_code = tmy3_meta.USAF[np.argmin(dis)]

        # read tmy3 data from archive using usaf code
        return pd.read_csv(
            f"{self.archive_tmy3_data_dir}/{usaf_code}TYA.CSV", skiprows=1
        )

    def get_psm3_tmy3(self, location):
        # TODO: finish implementing
        raise NotImplementedError

        lat = 43.83452
        lon = -99.49218
        # attributes to extract (e.g., dhi, ghi, etc.), separated by commas.
        attributes = ",".join(
            [
                "ghi",
                "dhi",
                "dni",
                "surface_pressure",
                "wind_direction",
                "wind_speed",
                "surface_albedo",
            ]
        )
        # Choose year of data
        names = "tmy"
        # local time zone or UTC (confirmed works for TMY3)
        utc = "true"

        # see: https://developer.nrel.gov/docs/solar/nsrdb/psm3-tmy-download/
        # email address is required
        url_tmy = (
            "https://developer.nrel.gov/api/nsrdb/v2/solar/psm3-tmy-download.csv"
            + f"?wkt=POINT({lon}%20{lat})"
            + f"&names={names}"
            + f"&api_key={self.nrel_dev_api_key}"
            + f"&attributes={attributes}"
            + f"&utc={utc}"
            + f"&email={self.nrel_dev_email}"
        )

        # Return just the first 2 lines to get metadata:
        meta = pd.read_csv(url_tmy, nrows=1)

        # skip info lines, 3rd line is header for data
        data = pd.read_csv(url_tmy, skiprows=2).reset_index()
        return data, meta

    def fill_epw(self, input_epw_data, datetime_channel, fill_epw_data, sim_config):
        """Any missing fields required by EnergyPlus should be filled with
        defaults from Typical Meteorological Year 3 data sets for nearest city.
        All data is internally in UTC.

        :param epw_data: EnergyPlus Weather data in a dataframe of epw_columns
        :type epw_data: pd.DataFrame

        :param datetime_column: datetime column in fill data.
        "type datetime_column: str
        """
        if input_epw_data.empty:
            input_epw_data.columns = self.epw_columns
            return input_epw_data

        if fill_epw_data.empty:
            raise ValueError(f"fill_epw_data is empty.")

        # save fill_epw_data that was actually used to fill
        self.fill_epw_data = fill_epw_data

        # edit unique copy of input df
        epw_data = input_epw_data.copy(deep=True)

        # add datetime column for merge with fill data
        epw_data = pd.concat(
            [
                datetime_channel.data[datetime_channel.spec.datetime_column],
                epw_data,
            ],
            axis="columns",
        ).rename(columns={datetime_channel.spec.datetime_column: self.datetime_column})

        # using annual TMY there may be missing rows at beginning
        # cycle from endtime to give full UTC year
        # wrap TMY data to fill any gaps
        if min(fill_epw_data[self.datetime_column]) > min(
            epw_data[self.datetime_column]
        ):
            # have data before fill data starts
            # wrap fill data on year
            time_diff = min(fill_epw_data[self.datetime_column]) - min(
                epw_data[self.datetime_column]
            )
            years = math.ceil(time_diff.days / 365.0)
            fill_epw_data_prev_years = []
            for y in range(1, years):
                _fill_epw_data_prev_year = fill_epw_data.copy(deep=True)
                _fill_epw_data_prev_year["year"] = _fill_epw_data_prev_year["year"] - 1
                _fill_epw_data_prev_year[
                    self.datetime_column
                ] = _fill_epw_data_prev_year[
                    self.datetime_column
                ] - pd.offsets.DateOffset(
                    years=1
                )
                fill_epw_data_prev_years.append(_fill_epw_data_prev_year)

            fill_epw_data = pd.concat(
                fill_epw_data_prev_years + [fill_epw_data], axis="rows"
            )
            fill_epw_data.sort_values(self.datetime_column)

        if max(fill_epw_data[self.datetime_column]) < max(
            epw_data[self.datetime_column]
        ):
            # have data before fill data starts
            # wrap fill data on year
            time_diff = max(epw_data[self.datetime_column]) - max(
                fill_epw_data[self.datetime_column]
            )
            years = math.ceil(time_diff.days / 365.0)
            fill_epw_data_prev_years = []
            for y in range(1, years):
                _fill_epw_data_prev_year = fill_epw_data.copy(deep=True)
                _fill_epw_data_prev_year["year"] = _fill_epw_data_prev_year["year"] + 1
                _fill_epw_data_prev_year[
                    self.datetime_column
                ] = _fill_epw_data_prev_year[
                    self.datetime_column
                ] + pd.offsets.DateOffset(
                    years=1
                )
                fill_epw_data_prev_years.append(_fill_epw_data_prev_year)

            fill_epw_data = pd.concat(
                [fill_epw_data] + fill_epw_data_prev_years, axis="rows"
            )
            fill_epw_data.sort_values(self.datetime_column)

        # get current period to check if resampling is needed
        _cur_fill_epw_data_period = (
            fill_epw_data[self.datetime_column].diff().mode()[0].total_seconds()
        )

        # resample to input frequency
        # the epw file may be at different step size than simulation due
        # to EnergyPlus model discretization being decoupled
        _input_data_period = (
            datetime_channel.data[datetime_channel.spec.datetime_column]
            .diff()
            .mode()[0]
            .total_seconds()
        )

        if _cur_fill_epw_data_period < _input_data_period:
            # downsample data
            fill_epw_data = (
                fill_epw_data.set_index(fill_epw_data[self.datetime_column])
                .resample(f"{_input_data_period}S")
                .mean()
                .reset_index()
            )
        elif _cur_fill_epw_data_period > _input_data_period:
            # upsample data
            fill_epw_data = fill_epw_data.set_index(self.datetime_column)
            fill_epw_data = fill_epw_data.resample(f"{_input_data_period}S").asfreq()
            # ffill is only method that works on all types
            fill_epw_data = fill_epw_data.interpolate(axis="rows", method="ffill")
            fill_epw_data = fill_epw_data.reset_index()

        # trim unused fill_epw_data
        fill_epw_data = fill_epw_data[
            (fill_epw_data[self.datetime_column] >= min(epw_data[self.datetime_column]))
            & (
                fill_epw_data[self.datetime_column]
                <= max(epw_data[self.datetime_column])
            )
        ].reset_index()

        # overwrite epw fill with input cols
        for _col, _epw_col in EnergyPlusWeather.output_rename_dict.items():
            if _col in epw_data.columns:
                if _epw_col in fill_epw_data.columns:
                    fill_epw_data[_epw_col] = epw_data[_col]

        # backfill missing input cols with epw fill
        for _col in self.epw_backfill_columns:
            if _col not in self.data.columns:
                _epw_col = EnergyPlusWeather.output_rename_dict[_col]
                if _epw_col in fill_epw_data.columns:
                    self.data[_col] = fill_epw_data[_epw_col]

        # resample to epw step size
        _cur_fill_epw_data_period = (
            fill_epw_data[self.datetime_column].diff().mode()[0].total_seconds()
        )
        if _cur_fill_epw_data_period < self.epw_step_size_seconds:
            # downsample data
            fill_epw_data = (
                fill_epw_data.set_index(fill_epw_data[self.datetime_column])
                .resample(f"{self.epw_step_size_seconds}S")
                .mean()
                .reset_index()
            )
        elif _cur_fill_epw_data_period > self.epw_step_size_seconds:
            # upsample data
            fill_epw_data = fill_epw_data.set_index(self.datetime_column)
            fill_epw_data = fill_epw_data.resample(
                f"{self.epw_step_size_seconds}S"
            ).asfreq()
            # ffill is only method that works on all types
            fill_epw_data = fill_epw_data.interpolate(axis="rows", method="ffill")
            fill_epw_data = fill_epw_data.reset_index()

        epw_data_full = fill_epw_data

        # compute dewpoint from dry-bulb and relative humidity
        epw_data_full["temp_dew"] = Conversions.relative_humidity_to_dewpoint(
            epw_data_full["temp_air"], epw_data_full["relative_humidity"]
        )

        # convert to local time INVARIANT to DST changes
        # .epw will have wrong hour columns if DST shift occurs during simulation
        # need a standard UTC offset for entire simulation period
        # no time zone shift occurs on or within 1 week of January 17th
        # use this for tz standard UTC offset
        tz_offset_seconds = datetime_channel.timezone.utcoffset(
            datetime(min(epw_data_full[self.datetime_column]).year, 1, 17)
        ).total_seconds()

        epw_data_full[self.datetime_column] = epw_data_full[
            self.datetime_column
        ] + pd.Timedelta(seconds=tz_offset_seconds)

        # last day of data must exist and be invariant to TZ shift
        # add ffill data for final day and extra day.
        _fill = epw_data_full.tail(1).copy(deep=True)
        _fill_rec = _fill.iloc[0]
        _fill[self.datetime_column] = _fill[self.datetime_column] + pd.Timedelta(
            days=2,
            hours=-_fill_rec[self.datetime_column].hour,
            minutes=-_fill_rec[self.datetime_column].minute,
            seconds=-_fill_rec[self.datetime_column].second,
        )
        epw_data_full = epw_data_full.append(_fill, ignore_index=True)
        epw_data_full = epw_data_full.set_index(self.datetime_column)

        # resample to building frequency
        epw_data_full = epw_data_full.resample(
            f"{self.epw_step_size_seconds}S"
        ).asfreq()
        # first ffill then bfill will fill both sides padding data
        epw_data_full = epw_data_full.fillna(method="ffill")
        epw_data_full = epw_data_full.fillna(method="bfill")
        epw_data_full = epw_data_full.reset_index()

        epw_data_full["year"] = epw_data_full[self.datetime_column].dt.year
        epw_data_full["month"] = epw_data_full[self.datetime_column].dt.month
        epw_data_full["day"] = epw_data_full[self.datetime_column].dt.day
        # energyplus uses non-standard hours [1-24] this is accounted in to_epw()
        epw_data_full["hour"] = epw_data_full[self.datetime_column].dt.hour
        epw_data_full["minute"] = epw_data_full[self.datetime_column].dt.minute

        # date time columns can be smaller dtypes
        epw_data_full = epw_data_full.astype(
            {
                "year": "Int16",
                "month": "Int8",
                "day": "Int8",
                "hour": "Int8",
                "minute": "Int8",
            },
        )

        # reorder return columns
        return epw_data_full

    def to_epw(
        self,
        epw_data,
        meta_lines,
        fpath,
    ):
        # EPW format uses hour = [1-24], set from [0-23] to [1-24]
        epw_data["hour"] = epw_data["hour"] + 1

        # use newline file buffer method to allow for writing lines
        # before pandas.to_csv writes data
        with open(fpath, "w") as f:
            # first add meta_lines
            for line in meta_lines:
                f.write(line)
            # add data after metalines
            epw_data[self.epw_columns].to_csv(f, header=False, index=False)

        return fpath


    #BCS - For this to work you must:
    # 1) install h5pyd:   pip install --user h5pyd
    # 2) Get your own API key, visit https://developer.nrel.gov/signup/
    # 3) configure HSDS:  Add the following contents to a configuration file at ~/.hscfg:
        # #HDFCloud configuration file
        # hs_endpoint = https://developer.nrel.gov/api/hsds
        # hs_username = None
        # hs_password = None
        # hs_api_key = <your api key here>
    def get_nsrdb(self,lat,long):
        
        # Unlike the gridded WTK data the NSRDB is provided as sparse time-series dataset.
        # The quickest way to find the nearest site it using a KDtree
        def nearest_site(tree, lat_coord, lon_coord):
            lat_lon = np.array([lat_coord, lon_coord])
            dist, pos = tree.query(lat_lon)
            return pos
        
        # Open the desired year of nsrdb data
        # server endpoint, username, password is found via a config file
        f = h5pyd.File("/nrel/nsrdb/v3/nsrdb_2019.h5", 'r')
        
        #create binary tree of coords for search
        dset_coords = f['coordinates'][...]
        tree = cKDTree(dset_coords)
        
        #identify nearest weather station
        location_idx = nearest_site(tree, lat, long)
        
        strPath = '' #TODO:  Create environment variable for nsrdb cache
        strFile = 'nsrdb_2019_{0:.2f}_{1:.2f}.csv.gz'.format(dset_coords[location_idx][0],dset_coords[location_idx][1])
        
        if not os.path.exists(strFile):
            print('Pulling nsrdb data')
            # Extract datetime index for datasets
            time_index = pd.to_datetime(f['time_index'][...].astype(str), utc=True)# Temporal resolution is 30min

            #get data sets
            dset_dni  = f['dni']
            dset_ghi  = f['ghi']
            dset_temp = f['air_temperature']
            dset_rh   = f['relative_humidity']
            # list(f)  # for full list the datasets in the file

            #filter on time series for given location
            tseries_dni  = dset_dni[:,  location_idx] / dset_dni.attrs['psm_scale_factor']  
            tseries_ghi  = dset_ghi[:,  location_idx] / dset_ghi.attrs['psm_scale_factor']  
            tseries_temp = dset_temp[:, location_idx] / dset_temp.attrs['psm_scale_factor'] 
            tseries_rh   = dset_rh[:,   location_idx] / dset_rh.attrs['psm_scale_factor']   

            #combine into single DF int
            df_solar = pd.DataFrame()
            df_solar["datetime"]          = time_index   # datetime64
            df_solar["dni"]               = tseries_dni  # W/m2, float
            df_solar["ghi"]               = tseries_ghi  # W/m2, float
            df_solar["temp_air"]          = tseries_temp # degC, float
            df_solar["relative_humidity"] = tseries_rh   # %rh,  float

            df_solar.to_csv(strPath + strFile, index=False, compression='gzip')
        else:
            print('Re-opening nsrdb data')
            df_solar = pd.read_csv(strFile, compression='gzip')
            df_solar.datetime = pd.to_datetime(df_solar.datetime)
        
        return strFile, df_solar
    # test:
    # strFile, df_solar = get_nsrdb(51.1739243, -114.1643148)
    # df_solar.info()


    fill_nsrdb_data = attr.ib(default=None)
    def fill_nsrdb(self, input_epw_data, datetime_channel, fill_nsrdb_data, sim_config):
        """Fill input data with NSRDB 2019 data as available.
        All data is internally in UTC.

        :param epw_data: EnergyPlus Weather data in a dataframe of epw_columns
        :type epw_data: pd.DataFrame

        :param datetime_column: datetime column in fill data.
        "type datetime_column: str
        """
        if input_epw_data.empty:
            input_epw_data.columns = self.epw_columns
            return input_epw_data

        if fill_nsrdb_data.empty:
            raise ValueError(f"fill_epw_data is empty.")

        # save fill_nsrdb_data that was actually used to fill
        self.fill_nsrdb_data = fill_nsrdb_data

        # edit unique copy of input df
        epw_data = input_epw_data.copy(deep=True)

        # add datetime column for merge with fill data
        epw_data = pd.concat(
            [
                datetime_channel.data[datetime_channel.spec.datetime_column],
                epw_data,
            ],
            axis="columns",
        ).rename(columns={datetime_channel.spec.datetime_column: self.datetime_column})

        # # using 2019 NSRDB data there may be missing rows at beginning
        # # cycle from endtime to give full UTC year
        # # wrap TMY data to fill any gaps
        # if min(fill_epw_data[self.datetime_column]) > min(
        #     epw_data[self.datetime_column]
        # ):
        #     # have data before fill data starts
        #     # wrap fill data on year
        #     time_diff = min(fill_epw_data[self.datetime_column]) - min(
        #         epw_data[self.datetime_column]
        #     )
        #     years = math.ceil(time_diff.days / 365.0)
        #     fill_epw_data_prev_years = []
        #     for y in range(1, years):
        #         _fill_epw_data_prev_year = fill_epw_data.copy(deep=True)
        #         _fill_epw_data_prev_year["year"] = _fill_epw_data_prev_year["year"] - 1
        #         _fill_epw_data_prev_year[
        #             self.datetime_column
        #         ] = _fill_epw_data_prev_year[
        #             self.datetime_column
        #         ] - pd.offsets.DateOffset(
        #             years=1
        #         )
        #         fill_epw_data_prev_years.append(_fill_epw_data_prev_year)

        #     fill_epw_data = pd.concat(
        #         fill_epw_data_prev_years + [fill_epw_data], axis="rows"
        #     )
        #     fill_epw_data.sort_values(self.datetime_column)

        # if max(fill_epw_data[self.datetime_column]) < max(
        #     epw_data[self.datetime_column]
        # ):
        #     # have data before fill data starts
        #     # wrap fill data on year
        #     time_diff = max(epw_data[self.datetime_column]) - max(
        #         fill_epw_data[self.datetime_column]
        #     )
        #     years = math.ceil(time_diff.days / 365.0)
        #     fill_epw_data_prev_years = []
        #     for y in range(1, years):
        #         _fill_epw_data_prev_year = fill_epw_data.copy(deep=True)
        #         _fill_epw_data_prev_year["year"] = _fill_epw_data_prev_year["year"] + 1
        #         _fill_epw_data_prev_year[
        #             self.datetime_column
        #         ] = _fill_epw_data_prev_year[
        #             self.datetime_column
        #         ] + pd.offsets.DateOffset(
        #             years=1
        #         )
        #         fill_epw_data_prev_years.append(_fill_epw_data_prev_year)

        #     fill_epw_data = pd.concat(
        #         [fill_epw_data] + fill_epw_data_prev_years, axis="rows"
        #     )
        #     fill_epw_data.sort_values(self.datetime_column)

        # get current period to check if resampling is needed
        _cur_fill_nsrdb_data_period = (
            fill_nsrdb_data[self.datetime_column].diff().mode()[0].total_seconds()
        )

        # resample to input frequency
        # the epw file may be at different step size than simulation due
        # to EnergyPlus model discretization being decoupled
        _input_data_period = (
            datetime_channel.data[datetime_channel.spec.datetime_column]
            .diff()
            .mode()[0]
            .total_seconds()
        )

        #TODO:  last nsrdb data point is dec 31, 23:30. Missing last half hr.
        if _cur_fill_nsrdb_data_period < _input_data_period:
            # downsample data
            fill_nsrdb_data = (
                fill_epw_data.set_index(fill_nsrdb_data[self.datetime_column])
                .resample(f"{_input_data_period}S")
                .mean()
                .reset_index()
            )
        elif _cur_fill_nsrdb_data_period > _input_data_period:
            # upsample data
            fill_nsrdb_data = fill_nsrdb_data.set_index(self.datetime_column)
            fill_nsrdb_data = fill_nsrdb_data.resample(f"{_input_data_period}S").asfreq()
            # ffill is only method that works on all types
            fill_nsrdb_data = fill_nsrdb_data.interpolate(axis="rows", method="linear")
            fill_nsrdb_data = fill_nsrdb_data.reset_index()

        # trim unused fill_nsrdb_data
        fill_nsrdb_data = fill_nsrdb_data[
            (fill_nsrdb_data[self.datetime_column] >= min(epw_data[self.datetime_column]))
            & (
                fill_nsrdb_data[self.datetime_column]
                <= max(epw_data[self.datetime_column])
            )
        ].reset_index()

        # overwrite epw fill with input cols
        for _col, _epw_col in EnergyPlusWeather.output_rename_dict.items():
            if _col in epw_data.columns:
                if _epw_col in fill_nsrdb_data.columns:
                    fill_nsrdb_data[_epw_col] = epw_data[_col]

        # backfill missing input cols with epw fill
        for _col in self.epw_backfill_columns:
            if _col not in self.data.columns:
                _epw_col = EnergyPlusWeather.output_rename_dict[_col]
                if _epw_col in fill_nsrdb_data.columns:
                    self.data[_col] = fill_nsrdb_data[_epw_col]

        # resample to epw step size
        _cur_fill_nsrdb_data_period = (
            fill_nsrdb_data[self.datetime_column].diff().mode()[0].total_seconds()
        )
        if _cur_fill_nsrdb_data_period < self.epw_step_size_seconds:
            # downsample data
            fill_nsrdb_data = (
                fill_nsrdb_data.set_index(fill_nsrdb_data[self.datetime_column])
                .resample(f"{self.epw_step_size_seconds}S")
                .mean()
                .reset_index()
            )
        elif _cur_fill_nsrdb_data_period > self.epw_step_size_seconds:
            # upsample data
            fill_nsrdb_data = fill_nsrdb_data.set_index(self.datetime_column)
            fill_nsrdb_data = fill_nsrdb_data.resample(
                f"{self.epw_step_size_seconds}S"
            ).asfreq()
            # ffill is only method that works on all types
            fill_nsrdb_data = fill_nsrdb_data.interpolate(axis="rows", method="linear")
            fill_nsrdb_data = fill_nsrdb_data.reset_index()

        nsrdb_data_full = fill_nsrdb_data
        # compute dewpoint from dry-bulb and relative humidity
        nsrdb_data_full["temp_dew"] = Conversions.relative_humidity_to_dewpoint(
            nsrdb_data_full["temp_air"], nsrdb_data_full["relative_humidity"]
        )

        # convert to local time INVARIANT to DST changes
        # .epw will have wrong hour columns if DST shift occurs during simulation
        # need a standard UTC offset for entire simulation period
        # no time zone shift occurs on or within 1 week of January 17th
        # use this for tz standard UTC offset
        tz_offset_seconds = datetime_channel.timezone.utcoffset(
            datetime(min(nsrdb_data_full[self.datetime_column]).year, 1, 17)
        ).total_seconds()

        nsrdb_data_full[self.datetime_column] = nsrdb_data_full[
            self.datetime_column
        ] + pd.Timedelta(seconds=tz_offset_seconds)

        # last day of data must exist and be invariant to TZ shift
        # add ffill data for final day and extra day.
        _fill = nsrdb_data_full.tail(1).copy(deep=True)
        _fill_rec = _fill.iloc[0]
        _fill[self.datetime_column] = _fill[self.datetime_column] + pd.Timedelta(
            days=2,
            hours=-_fill_rec[self.datetime_column].hour,
            minutes=-_fill_rec[self.datetime_column].minute,
            seconds=-_fill_rec[self.datetime_column].second,
        )
        nsrdb_data_full = nsrdb_data_full.append(_fill, ignore_index=True)
        nsrdb_data_full = nsrdb_data_full.set_index(self.datetime_column)

        # resample to building frequency
        nsrdb_data_full = nsrdb_data_full.resample(
            f"{self.epw_step_size_seconds}S"
        ).asfreq()
        # first ffill then bfill will fill both sides padding data
        nsrdb_data_full = nsrdb_data_full.fillna(method="ffill")
        nsrdb_data_full = nsrdb_data_full.fillna(method="bfill")
        nsrdb_data_full = nsrdb_data_full.reset_index()

        nsrdb_data_full["year"] = nsrdb_data_full[self.datetime_column].dt.year
        nsrdb_data_full["month"] = nsrdb_data_full[self.datetime_column].dt.month
        nsrdb_data_full["day"] = nsrdb_data_full[self.datetime_column].dt.day
        # energyplus uses non-standard hours [1-24] this is accounted in to_epw()
        nsrdb_data_full["hour"] = nsrdb_data_full[self.datetime_column].dt.hour
        nsrdb_data_full["minute"] = nsrdb_data_full[self.datetime_column].dt.minute

        # date time columns can be smaller dtypes
        nsrdb_data_full = nsrdb_data_full.astype(
            {
                "year": "Int16",
                "month": "Int8",
                "day": "Int8",
                "hour": "Int8",
                "minute": "Int8",
            },
        )

        # reorder return columns
        return nsrdb_data_full