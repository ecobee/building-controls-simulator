# created by Tom Stesco tom.s@ecobee.com

import os
import logging

import pandas as pd
import attr
import numpy as np
from google.cloud import storage

from pvlib.forecast import GFS, NAM, HRRR, RAP, NDFD

from BuildingControlsSimulator.DataClients.DataClient import DataClient

logger = logging.getLogger(__name__)


@attr.s(kw_only=True)
class EnergyPlusWeather(object):
    """Connector for generating EPW files.
    See:
    https://pvlib-python.readthedocs.io/en/stable/_modules/pvlib/iotools/epw.html

    """

    start_time_UTC = attr.ib()
    end_time_UTC = attr.ib()
    data_dir = attr.ib()

    headers = attr.ib(
        default=[
            "loc",
            "city",
            "state-prov",
            "country",
            "data_type",
            "WMO_code",
            "latitude",
            "longitude",
            "TZ",
            "altitude",
        ]
    )

    colnames = attr.ib(
        default=[
            "year",
            "month",
            "day",
            "hour",
            "minute",
            "data_source_unct",
            "temp_air",
            "temp_dew",
            "relative_humidity",
            "atmospheric_pressure",
            "etr",
            "etrn",
            "ghi_infrared",
            "ghi",
            "dni",
            "dhi",
            "global_hor_illum",
            "direct_normal_illum",
            "diffuse_horizontal_illum",
            "zenith_luminance",
            "wind_direction",
            "wind_speed",
            "total_sky_cover",
            "opaque_sky_cover",
            "visibility",
            "ceiling_height",
            "present_weather_observation",
            "present_weather_codes",
            "precipitable_water",
            "aerosol_optical_depth",
            "snow_depth",
            "days_since_last_snowfall",
            "albedo",
            "liquid_precipitation_depth",
            "liquid_precipitation_quantity",
        ]
    )

    data_source = attr.ib(default="dyd")
    gcs_project = attr.ib(default="datascience-181217")
    gcs_bucket = attr.ib(default="donate_your_data_2019")
    weather_dir = attr.ib(default=os.environ.get("WEATHER_DIR"))

    meta_dir = attr.ib(
        default=os.path.join(
            os.environ.get("PACKAGE_DIR"), "data", "dyd", "meta"
        )
    )
    meta_fname = attr.ib(default="meta_data.csv")
    meta_gs_uri = attr.ib(default="gs://donate_your_data_2019/meta_data.csv")

    latitude = attr.ib(default=None)
    longitude = attr.ib(default=None)
    timezone = attr.ib(default=None)

    postal_code = attr.ib(default=None)

    country = attr.ib(default=None)
    prov_state = attr.ib(default=None)
    city = attr.ib(default=None)

    forecast_model = attr.ib(default=None)

    # local or distributed hosting
    backing = attr.ib(default="local")

    def __attrs_post_init__(self):
        """
        """
        # convert to UTC timestamp
        self.start_time_UTC = pd.Timestamp(self.start_time_UTC, tz="UTC")
        self.end_time_UTC = pd.Timestamp(self.end_time_UTC, tz="UTC")

        # for local hosting save files on local machine
        if self.backing == "local":
            os.makedirs(self.data_dir, exist_ok=True)
            os.makedirs(self.meta_dir, exist_ok=True)

        if self.forecast_model == "GFS":
            self.model = GFS()
        elif self.forecast_model == "HRRR":
            self.model = HRRR()
        elif self.forecast_model == "RAP":
            self.model = RAP()
        elif self.forecast_model == "NAM":
            self.model = NAM()
        else:
            self.model = NDFD()

    def get_data(self):
        return self.model.get_processed_data(
            self.latitude,
            self.longitude,
            self.start_time_UTC,
            self.end_time_UTC,
        )

    def find_tmy_data(self, locations):
        """
        """
        [("US", "AZ", "Phoenix")]
        pass
