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
    epw_meta_lines = attr.ib(factory=list)
    epw_fname = attr.ib(default=None)
    epw_step_size_seconds = attr.ib(default=None)
    weather_forecast_source = attr.ib(default=None)
    forecast_data = attr.ib(default=None)
    forecasts = attr.ib(default=None)

    # env variables
    ep_tmy3_cache_dir = attr.ib()
    nsrdb_cache_dir = attr.ib()
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

    # these are the weather data columns that we will backfill with epw data
    epw_backfill_columns = attr.ib()

    @epw_backfill_columns.default
    def get_epw_backfill_columns(self):
        return [
            STATES.DIRECT_NORMAL_IRRADIANCE,
            STATES.GLOBAL_HORIZONTAL_IRRADIANCE,
            STATES.DIFFUSE_HORIZONTAL_IRRADIANCE,
        ]

    # these are the solar radiation columns defined for unit conversions
    epw_radiation_columns = attr.ib()

    @epw_radiation_columns.default
    def get_epw_radiation_columns(self):
        return [
            "etr",
            "etrn",
            "ghi_infrared",
            "ghi",
            "dni",
            "dhi",
        ]

    def get_epw_data(
        self,
        sim_config,
        datetime_channel,
        epw_path=None,
    ):
        """Get epw file and read it, then preprocess to internal spec"""
        if epw_path:
            if os.path.exists(epw_path):
                self.epw_fname = os.path.basename(epw_path)
            else:
                ValueError(f"epw_path: {epw_path} does not exist.")
        else:
            # attempt to get .epw data from NREL
            epw_path, self.epw_fname = self.get_tmy_epw(
                sim_config["latitude"], sim_config["longitude"]
            )

        (epw_data, self.epw_meta, self.epw_meta_lines,) = self.read_epw(
            epw_path,
        )

        self.epw_step_size_seconds = sim_config["sim_step_size_seconds"]

        # infer if the years in the epw file are garbage from TMY
        # TMY data is only valid for a period of 1 year and then it must
        # be wrapped to next year if required for multi-year weather data
        # the year supplied in TMY data is not a valid sequential time
        # Therefore the year must be overwritten to desired year
        force_year = None
        if len(epw_data["year"].unique()) > 2 and (len(epw_data["year"]) < 8762):
            # it is not possible to have full consequtive data for 3 different
            # years and less than 8762 total data points.

            # using the mode will handle the case of shifting data points into
            # adjacent years
            force_year = (
                datetime_channel.data[datetime_channel.spec.datetime_column]
                .dt.year.mode()
                .values[0]
            )

        epw_data = self.convert_epw_to_internal(
            epw_data,
            force_year=force_year,
        )

        # lat/lon time zone is the time zone we localize with
        # the datetime_channel timezone is free to be changed later
        _hour_offset = (
            datetime_channel.timezone.utcoffset(datetime(2019, 1, 1)).total_seconds()
            / 3600
        )
        if self.epw_meta["TZ"] != _hour_offset:
            logger.warn(
                "Timezones from longitude and latitude and given epw do not match."
            )
            self.epw_meta["TZ"] = _hour_offset

        if not epw_data.empty:
            # fill any missing fields in epw
            # need to pass in original dyd datetime column name
            self.data, epw_data = self.merge_data_with_epw(
                self.data, epw_data, datetime_channel
            )

        else:
            logger.error("failed to retrieve .epw fill data.")

        self.epw_data = epw_data

    def merge_data_with_epw(self, data, epw_data, datetime_channel):
        # add datetime column for merge with fill data
        data = pd.concat(
            [
                datetime_channel.data[datetime_channel.spec.datetime_column],
                data,
            ],
            axis="columns",
        ).rename(columns={datetime_channel.spec.datetime_column: self.datetime_column})

        # using annual TMY there may be missing rows at beginning
        # cycle from endtime to give full UTC year
        # wrap TMY data to fill any gaps
        if min(epw_data[self.datetime_column]) > min(data[self.datetime_column]):
            # have data before fill data starts
            # wrap fill data on year
            time_diff = min(epw_data[self.datetime_column]) - min(
                data[self.datetime_column]
            )
            years = math.ceil(time_diff.days / 365.0)
            epw_data_prev_years = []
            for y in range(1, years):
                _epw_data_prev_year = epw_data.copy(deep=True)
                _epw_data_prev_year["year"] = _epw_data_prev_year["year"] - 1
                _epw_data_prev_year[self.datetime_column] = _epw_data_prev_year[
                    self.datetime_column
                ] - pd.offsets.DateOffset(years=1)
                epw_data_prev_years.append(_epw_data_prev_year)

            epw_data = pd.concat(epw_data_prev_years + [epw_data], axis="rows")
            epw_data.sort_values(self.datetime_column)

        if max(epw_data[self.datetime_column]) < max(data[self.datetime_column]):
            # have data before fill data starts
            # wrap fill data on year
            time_diff = max(epw_data[self.datetime_column]) - max(
                data[self.datetime_column]
            )
            years = math.ceil(time_diff.days / 365.0)
            epw_data_prev_years = []
            for y in range(1, years):
                _epw_data_prev_year = epw_data.copy(deep=True)
                _epw_data_prev_year["year"] = _epw_data_prev_year["year"] + 1
                _epw_data_prev_year[self.datetime_column] = _epw_data_prev_year[
                    self.datetime_column
                ] + pd.offsets.DateOffset(years=1)
                epw_data_prev_years.append(_epw_data_prev_year)

            epw_data = pd.concat([epw_data] + epw_data_prev_years, axis="rows")
            epw_data.sort_values(self.datetime_column)

        # get current period to check if resampling is needed
        _cur_epw_data_period = (
            epw_data[self.datetime_column].diff().mode()[0].total_seconds()
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

        if _cur_epw_data_period < _input_data_period:
            # downsample data
            epw_data = (
                epw_data.set_index(epw_data[self.datetime_column])
                .resample(f"{_input_data_period}S")
                .mean()
                .reset_index()
            )
        elif _cur_epw_data_period > _input_data_period:
            # upsample data
            epw_data = epw_data.set_index(self.datetime_column)
            epw_data = epw_data.resample(f"{_input_data_period}S").asfreq()
            # ffill is only method that works on all types
            epw_data = epw_data.interpolate(axis="rows", method="ffill")
            epw_data = epw_data.reset_index()

        # radiation columns unit converstion Wh/m2 -> W/m2
        epw_data.loc[:, self.epw_radiation_columns] = epw_data.loc[
            :, self.epw_radiation_columns
        ] / (_cur_epw_data_period / 3600.0)

        # trim unused epw_data
        epw_data = epw_data[
            (epw_data[self.datetime_column] >= min(data[self.datetime_column]))
            & (epw_data[self.datetime_column] <= max(data[self.datetime_column]))
        ].reset_index()

        # overwrite epw fill with input cols
        for _col, _epw_col in EnergyPlusWeather.output_rename_dict.items():
            if (_col in data.columns) and (_epw_col in epw_data.columns):
                epw_data[_epw_col] = data[_col]

        # backfill missing input cols with epw fill
        for _col in self.epw_backfill_columns:
            if _col not in data.columns:
                _epw_col = EnergyPlusWeather.output_rename_dict[_col]
                if _epw_col in epw_data.columns:
                    data[_col] = epw_data[_epw_col]

        # drop self.datetime_column
        data = data.drop(columns=[self.datetime_column])

        return data, epw_data

    def make_epw_file(
        self,
        sim_config,
        datetime_channel,
        epw_step_size_seconds,
    ):
        """Generate epw file in local time"""
        if self.epw_data.empty:
            raise ValueError(f"No input: epw_data={epw_data} and epw_path={epw_path}")

        self.epw_step_size_seconds = epw_step_size_seconds

        _epw_path = os.path.join(
            self.simulation_epw_dir,
            "NREL_EPLUS" + f"_{sim_config['identifier']}" + f"_{self.epw_fname}",
        )

        # resample
        _cur_epw_data_period = (
            self.epw_data[self.datetime_column].diff().mode()[0].total_seconds()
        )
        if _cur_epw_data_period < self.epw_step_size_seconds:
            # downsample data
            self.epw_data = (
                self.epw_data.set_index(self.epw_data[self.datetime_column])
                .resample(f"{self.epw_step_size_seconds}S")
                .mean()
                .reset_index()
            )
        elif _cur_epw_data_period > self.epw_step_size_seconds:
            # upsample data
            self.epw_data = self.epw_data.set_index(self.datetime_column)
            self.epw_data = self.epw_data.resample(
                f"{self.epw_step_size_seconds}S"
            ).asfreq()
            # ffill is only method that works on all types
            self.epw_data = self.epw_data.interpolate(axis="rows", method="ffill")
            self.epw_data = self.epw_data.reset_index()

        # NOTE:
        # EnergyPlus assumes solar radiance is given in W/m2 instead of Wh/m2
        # if more than one data interval per hour is given
        # see: https://github.com/NREL/EnergyPlus/blob/v9.4.0/src/EnergyPlus/WeatherManager.cc#L3147

        # compute dewpoint from dry-bulb and relative humidity
        self.epw_data["temp_dew"] = Conversions.relative_humidity_to_dewpoint(
            self.epw_data["temp_air"], self.epw_data["relative_humidity"]
        )

        # convert to local time INVARIANT to DST changes
        # .epw will have wrong hour columns if DST shift occurs during simulation
        # need a standard UTC offset for entire simulation period
        # no time zone shift occurs on or within 1 week of January 17th
        # use this for tz standard UTC offset
        tz_offset_seconds = datetime_channel.timezone.utcoffset(
            datetime(min(self.epw_data[self.datetime_column]).year, 1, 17)
        ).total_seconds()

        self.epw_data[self.datetime_column] = self.epw_data[
            self.datetime_column
        ] + pd.Timedelta(seconds=tz_offset_seconds)

        # last day of data must exist and be invariant to TZ shift
        # add ffill data for final day and extra day.
        _fill = self.epw_data.tail(1).copy(deep=True)
        _fill_rec = _fill.iloc[0]
        _fill[self.datetime_column] = _fill[self.datetime_column] + pd.Timedelta(
            days=2,
            hours=-_fill_rec[self.datetime_column].hour,
            minutes=-_fill_rec[self.datetime_column].minute,
            seconds=-_fill_rec[self.datetime_column].second,
        )
        self.epw_data = self.epw_data.append(_fill, ignore_index=True)
        self.epw_data = self.epw_data.set_index(self.datetime_column)

        # resample to building frequency
        self.epw_data = self.epw_data.resample(
            f"{self.epw_step_size_seconds}S"
        ).asfreq()
        # first ffill then bfill will fill both sides padding data
        self.epw_data = self.epw_data.fillna(method="ffill")
        self.epw_data = self.epw_data.fillna(method="bfill")
        self.epw_data = self.epw_data.reset_index()

        self.epw_data["year"] = self.epw_data[self.datetime_column].dt.year
        self.epw_data["month"] = self.epw_data[self.datetime_column].dt.month
        self.epw_data["day"] = self.epw_data[self.datetime_column].dt.day
        # energyplus uses non-standard hours [1-24] this is accounted in to_epw()
        self.epw_data["hour"] = self.epw_data[self.datetime_column].dt.hour
        self.epw_data["minute"] = self.epw_data[self.datetime_column].dt.minute

        # date time columns can be smaller dtypes
        self.epw_data = self.epw_data.astype(
            {
                "year": "Int16",
                "month": "Int8",
                "day": "Int8",
                "hour": "Int8",
                "minute": "Int8",
            },
        )

        meta_lines = self.add_epw_data_periods(
            epw_data=self.epw_data,
            meta_lines=self.epw_meta_lines,
            sim_config=sim_config,
        )

        # save to file
        self.to_epw(
            epw_data=self.epw_data,
            meta_lines=meta_lines,
            fpath=_epw_path,
        )

        self.epw_path = _epw_path

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

    def get_tmy_epw(self, lat, lon):

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

    # Unlike the gridded WTK data the NSRDB is provided as sparse time-series dataset.
    # The quickest way to find the nearest site it using a KDtree
    @staticmethod
    def nearest_site(tree, lat_coord, lon_coord):
        lat_lon = np.array([lat_coord, lon_coord])
        dist, idx = tree.query(lat_lon)
        return idx

    @staticmethod
    def manage_hscfg(nrel_dev_api_key):
        # Get your own API key, visit https://developer.nrel.gov/signup/
        # remove and create NREL HSDS configuration file at ~/.hscfg:
        hscfg_path = os.path.expanduser("~/.hscfg")
        if os.path.isfile(hscfg_path):
            os.remove(hscfg_path)

        _lines = [
            "hs_endpoint = https://developer.nrel.gov/api/hsds\n",
            "hs_username = None\n",
            "hs_password = None\n",
            f"hs_api_key = {nrel_dev_api_key}\n",
        ]

        with open(hscfg_path, "w") as f:
            f.writelines(_lines)

    def fill_nsrdb(self, input_data, datetime_channel, sim_config):
        """Fill input data with NSRDB 2019 data as available.
        All data is internally in UTC.
        """
        if input_data.empty:
            raise ValueError(f"input_data is empty.")

        # if nrel API key is not set, return input
        if not self.nrel_dev_api_key:
            return input_data

        WeatherChannel.manage_hscfg(self.nrel_dev_api_key)

        # Open the desired year of nsrdb data
        # server endpoint, username, password is found via a config file
        f = h5pyd.File(
            "/nrel/nsrdb/v3/nsrdb_{}.h5".format(str(sim_config["start_utc"].year)), "r"
        )

        # create binary tree of coords for search
        dset_coords = f["coordinates"][...]
        tree = cKDTree(dset_coords)

        # identify nearest weather station
        location_idx = WeatherChannel.nearest_site(
            tree, sim_config["latitude"], sim_config["longitude"]
        )

        fname = "nsrdb_{0}_{1:.2f}_{2:.2f}.csv.gz".format(
            str(sim_config["start_utc"].year),
            dset_coords[location_idx][0],
            dset_coords[location_idx][1],
        )

        fpath = os.path.join(self.nsrdb_cache_dir, fname)

        if not os.path.exists(fpath):
            logger.info("Pulling nsrdb data")

            # Extract datetime index for datasets
            time_index = pd.to_datetime(
                f["time_index"][...].astype(str), utc=True
            )  # Temporal resolution is 30min

            # get data sets
            dset_dni = f["dni"]
            dset_ghi = f["ghi"]
            dset_temp = f["air_temperature"]
            dset_rh = f["relative_humidity"]
            # list(f)  # for full list the datasets in the file

            # filter on time series for given location
            tseries_dni = dset_dni[:, location_idx] / dset_dni.attrs["psm_scale_factor"]
            tseries_ghi = dset_ghi[:, location_idx] / dset_ghi.attrs["psm_scale_factor"]
            tseries_temp = (
                dset_temp[:, location_idx] / dset_temp.attrs["psm_scale_factor"]
            )
            tseries_rh = dset_rh[:, location_idx] / dset_rh.attrs["psm_scale_factor"]

            # combine into single DF int
            fill_nsrdb_data = pd.DataFrame()
            fill_nsrdb_data["datetime"] = time_index  # datetime64
            fill_nsrdb_data["dni"] = tseries_dni  # W/m2, float
            fill_nsrdb_data["ghi"] = tseries_ghi  # W/m2, float
            fill_nsrdb_data["temp_air"] = tseries_temp  # degC, float
            fill_nsrdb_data["relative_humidity"] = tseries_rh  # %rh,  float

            fill_nsrdb_data.to_csv(fpath, index=False, compression="gzip")
        else:
            logger.info("Reading from local cache NSRDB data")
            fill_nsrdb_data = pd.read_csv(fpath, compression="gzip")
            fill_nsrdb_data.datetime = pd.to_datetime(fill_nsrdb_data.datetime)

        if fill_nsrdb_data.empty:
            raise ValueError(f"fill_nsrdb_data is empty.")

        # save fill_nsrdb_data that was actually used to fill
        self.fill_nsrdb_data = fill_nsrdb_data

        # add datetime column for merge with fill data
        input_data = pd.concat(
            [
                datetime_channel.data[datetime_channel.spec.datetime_column],
                input_data,
            ],
            axis="columns",
        ).rename(columns={datetime_channel.spec.datetime_column: self.datetime_column})

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

        # TODO:  last nsrdb data point is dec 31, 23:30. Missing last half hr.
        if _cur_fill_nsrdb_data_period < _input_data_period:
            # downsample data
            fill_nsrdb_data = (
                fill_nsrdb_data.set_index(fill_nsrdb_data[self.datetime_column])
                .resample(f"{_input_data_period}S")
                .mean()
                .reset_index()
            )
        elif _cur_fill_nsrdb_data_period > _input_data_period:
            # upsample data
            fill_nsrdb_data = fill_nsrdb_data.set_index(self.datetime_column)
            fill_nsrdb_data = fill_nsrdb_data.resample(
                f"{_input_data_period}S"
            ).asfreq()
            # ffill is only method that works on all types
            fill_nsrdb_data = fill_nsrdb_data.interpolate(axis="rows", method="linear")
            fill_nsrdb_data = fill_nsrdb_data.reset_index()

        # trim unused fill_nsrdb_data
        fill_nsrdb_data = fill_nsrdb_data[
            (
                fill_nsrdb_data[self.datetime_column]
                >= min(input_data[self.datetime_column])
            )
            & (
                fill_nsrdb_data[self.datetime_column]
                <= max(input_data[self.datetime_column])
            )
        ].reset_index()

        # overwrite nsrdb fill with input cols
        for _col, _epw_col in EnergyPlusWeather.output_rename_dict.items():
            if (_col in input_data.columns) and (_epw_col in fill_nsrdb_data.columns):
                fill_nsrdb_data[_epw_col] = input_data[_col]

        # backfill missing input cols with epw fill
        for _col in self.epw_backfill_columns:
            if _col not in self.data.columns:
                _epw_col = EnergyPlusWeather.output_rename_dict[_col]
                if _epw_col in fill_nsrdb_data.columns:
                    input_data[_col] = fill_nsrdb_data[_epw_col]

        input_data = input_data.drop(columns=[self.datetime_column])

        return input_data

    def get_forecast_data(self, sim_config, total_sim_steps):
        if self.weather_forecast_source != "perfect":
            # for other forecasting paradigms than perfect the forecast data must
            # be interpolated to the simulation frequency
            raise NotImplementedError(
                "Only weather_forecast_source=perfect is implemented."
            )
            self.forecasts = []
            step_size_seconds = sim_config["sim_step_size_seconds"]
            max_horizon_steps = 86400 // step_size_seconds
            if self.weather_forecast_source == "perfect":
                # use measured weather data directly as perfect forecast
                for idx in range(1, total_sim_steps):
                    self.forecasts.append(
                        forecast_data[idx : (idx + max_horizon_steps)].reset_index(
                            drop=True
                        )
                    )
