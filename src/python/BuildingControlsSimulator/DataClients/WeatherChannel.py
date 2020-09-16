# created by Tom Stesco tom.s@ecobee.com

import os
import logging
import re

import pandas as pd
import numpy as np
import attr
import requests
from sklearn.metrics.pairwise import haversine_distances

from BuildingControlsSimulator.DataClients.DataSpec import EnergyPlusWeather
from BuildingControlsSimulator.DataClients.DataChannel import DataChannel
from BuildingControlsSimulator.Conversions.Conversions import Conversions


logger = logging.getLogger(__name__)


@attr.s(kw_only=True)
class WeatherChannel(DataChannel):
    """Client for weather data.
    """

    epw_fpath = attr.ib(default=None)
    epw_data = attr.ib(default={})
    epw_meta = attr.ib(default={})

    # env variables
    nrel_dev_api_key = attr.ib(default=None)
    nrel_dev_email = attr.ib(default=None)
    archive_tmy3_meta = attr.ib(default=None)
    archive_tmy3_data_dir = attr.ib()
    ep_tmy3_cache_dir = attr.ib()
    simulation_epw_dir = attr.ib()

    # column names
    datetime_column = attr.ib(default=EnergyPlusWeather.datetime_column)
    epw_columns = attr.ib(default=EnergyPlusWeather.epw_columns)
    epw_meta_keys = attr.ib(default=EnergyPlusWeather.epw_meta)
    epw_column_map = attr.ib(default=EnergyPlusWeather.output_rename_dict)

    def get_epw_path(self, identifier, fill_epw_fname):
        os.path.join(
            self.simulation_epw_dir,
            f"{self.data_source_name}"
            + f"_{identifier}"
            + f"_{fill_epw_fname}",
        )

    def make_epw_file(self, sim_config):
        _epw_fpath = None
        # attempt to get .epw data from NREL
        fill_epw_fpath, fill_epw_fname = self.get_tmy_epw(
            sim_config["latitude"], sim_config["longitude"]
        )
        (fill_epw_data, epw_meta, meta_lines,) = self.read_epw(fill_epw_fpath)

        if not fill_epw_data.empty:
            _epw_fpath = os.path.join(
                self.simulation_epw_dir,
                "NREL_EPLUS"
                + f"_{sim_config['identifier']}"
                + f"_{fill_epw_fname}",
            )

            # fill any missing fields in epw
            # need to pass in original dyd datetime column name
            epw_data = self.fill_epw(self.data, fill_epw_data,)

            # save to file
            self.to_epw(
                epw_data=epw_data,
                meta=epw_meta,
                meta_lines=meta_lines,
                fpath=_epw_fpath,
            )

            self.epw_fpath = _epw_fpath
        else:
            logger.error("failed to retrieve .epw fill data.")

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

        meta = dict(
            zip(self.epw_meta_keys, meta_epw_lines[0].rstrip("\n").split(","))
        )
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

        # some EPW files have minutes=60 to represent the end of the hour
        # this doesnt actually mean it is the next hour, it should be 0
        # see: https://discourse.radiance-online.org/t/ \
        # meaning-of-epw-files-minute-field-and-why-is-it-60-in-tmy2- \
        # based-epw-and-0-in-tmy3-based-epw/1462/3
        if data["minute"].mean() == 60:
            data["minute"] = 0

        # EPW format uses hour = [1-24], set to [0-23]
        data["hour"] = data["hour"] - 1

        # create datetime column in UTC
        dt_cols = (
            data[["year", "month", "day", "hour", "minute"]]
            .astype("str")
            .apply(lambda x: x.str.zfill(2))
        )
        # create string column with compact format="%Y%m%d%H%M"
        dt_str_col = (
            dt_cols["year"]
            + dt_cols["month"]
            + dt_cols["day"]
            + dt_cols["hour"]
            + dt_cols["minute"]
        )

        data[self.datetime_column] = pd.to_datetime(
            dt_str_col.astype("str"), format="%Y%m%d%H%M"
        )
        # localize and convert to UTC
        data[self.datetime_column] = (
            data[self.datetime_column]
            .dt.tz_localize(int(meta["TZ"] * 3600))
            .dt.tz_convert(tz="UTC")
        )
        # there will be missing columns at beginning
        # cycle from endtime to give full UTC year
        tz_shift = int(meta["TZ"])
        if tz_shift != 0:
            data = pd.concat(
                [data[tz_shift : len(data)], data[0:tz_shift]]
            ).reset_index(drop=True)

        # alter meta data to show UTC after converting to UTC
        meta["TZ"] = 0
        meta_epw_lines[0] = ",".join([str(v) for _, v in meta.items()]) + "\n"

        # reset year, month, day, hour, minute columns
        data["year"] = data[self.datetime_column].dt.year
        data["month"] = data[self.datetime_column].dt.month
        data["day"] = data[self.datetime_column].dt.day
        data["hour"] = data[self.datetime_column].dt.hour
        data["minute"] = data[self.datetime_column].dt.minute

        return data, meta, meta_epw_lines

    def get_cdo(self):
        # TODO:
        # https://www.ncdc.noaa.gov/cdo-web/webservices/v2#gettingStarted
        pass

    def get_psm(self, location):
        # TODO:
        # url = (
        #     "https://developer.nrel.gov/api/nsrdb/v2/solar/psm3-tmy-download.csv"
        #     + f"?wkt=POINT({lon}%20{lat})&names={year}&leap_day={leap_year}"
        #     + f"&api_key={self.nrel_dev_api_key}&attributes={attributes}"
        #     + f"&utc={utc}&full_name={name}&email={email}&interval={interval}"
        # )
        pass

    def get_tmy_epw(self, lat, lon):
        # convert query point to radians and set dimensionality to (2,1)
        qp = np.radians(np.atleast_2d(np.array([lat, lon])))

        df = pd.json_normalize(
            pd.read_json(
                "https://raw.githubusercontent.com/NREL/EnergyPlus/develop/weather/master.geojson"
            ).features
        )

        # the geojson coordinates are [lon, lat]
        df_coord = pd.DataFrame(
            df["geometry.coordinates"].to_list(), columns=["lon", "lat"]
        )
        df_coord["lat"] = np.radians(df_coord["lat"])
        df_coord["lon"] = np.radians(df_coord["lon"])

        dis = haversine_distances(df_coord[["lat", "lon"]].values, qp)

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
        dis = haversine_distances(
            tmy3_meta[["Latitude", "Longitude"]].values, qp
        )

        # station that minimizes distance from query point should be used
        usaf_code = tmy3_meta.USAF[np.argmin(dis)]

        # read tmy3 data from archive using usaf code
        return pd.read_csv(
            f"{self.archive_tmy3_data_dir}/{usaf_code}TYA.CSV", skiprows=1
        )

    def get_psm3_tmy3(self, location):
        # TODO: finish implementing
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

    def fill_epw(self, epw_data, fill_data):
        """Any missing fields required by EnergyPlus should be filled with
        defaults from Typical Meteorological Year 3 data sets for nearest city.
        All data is internally in UTC.

        :param epw_data: EnergyPlus Weather data in a dataframe of epw_columns
        :type epw_data: pd.DataFrame

        :param datetime_column: datetime column in fill data.
        "type datetime_column: str
        """
        # edit unique copy of input df
        epw_data = epw_data.copy(deep=True)

        # only need to resample and fill if records not empty
        if len(epw_data) > 0:

            # resample to hourly data
            # the minute value has no meaning, it being 60 is not meaningful
            epw_data = (
                epw_data.set_index(epw_data[self.spec.datetime_column])
                .resample("1H")
                .mean()
                .reset_index()
            )
            epw_data["year"] = epw_data[self.spec.datetime_column].dt.year
            epw_data["month"] = epw_data[self.spec.datetime_column].dt.month
            epw_data["day"] = epw_data[self.spec.datetime_column].dt.day
            epw_data["hour"] = epw_data[self.spec.datetime_column].dt.hour
            # average minutes is incorrect, should just be 0
            epw_data["minute"] = 0

            # compare fill_data and real weather data
            fill_data = fill_data.merge(
                epw_data[["month", "day", "hour"] + self.spec.columns],
                how="outer",
                on=["month", "day", "hour"],
            )
            # loop over spec columns and replace missing values
            for _col in self.spec.columns:
                fill_data.loc[fill_data[_col].isnull(), _col,] = fill_data[
                    EnergyPlusWeather.output_rename_dict[_col]
                ]

                fill_data[
                    EnergyPlusWeather.output_rename_dict[_col]
                ] = fill_data[_col]

                fill_data = fill_data.drop(columns=[_col])

            # compute dewpoint from dry-bulb and relative humidity
            fill_data["temp_dew"] = Conversions.relative_humidity_to_dewpoint(
                fill_data["temp_air"], fill_data["relative_humidity"]
            )

            # date time columns can be smaller dtypes
            fill_data = fill_data.astype(
                {
                    "year": "Int16",
                    "month": "Int8",
                    "day": "Int8",
                    "hour": "Int8",
                    "minute": "Int8",
                },
            )

        # reorder return columns
        return fill_data[self.epw_columns]

    def to_epw(self, epw_data, meta, meta_lines, fpath):

        # EPW format uses hour = [1-24], set from [0-23] to [1-24]
        epw_data["hour"] = epw_data["hour"] + 1

        # use newline file buffer method to allow for writing lines
        # before pandas.to_csv writes data
        with open(fpath, "w") as f:
            # first add meta_lines
            for line in meta_lines:
                f.write(line)
            # add data after metalines
            epw_data.to_csv(f, header=False, index=False)

        return fpath
