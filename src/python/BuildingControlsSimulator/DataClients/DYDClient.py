# created by Tom Stesco tom.s@ecobee.com

import os
import logging

import pandas as pd
import attr
import numpy as np

# from google.cloud import storage

from BuildingControlsSimulator.DataClients.DataClient import DataClient

logger = logging.getLogger(__name__)


@attr.s(kw_only=True)
class DYDClient(DataClient):
    """Client for DYD data.
    DYD is implemented as a GCS hosted cache.
    """

    data_source_name = attr.ib(default="dyd")

    # meta_fname = attr.ib(default="meta_data.csv")
    meta_gs_uri = attr.ib(default=os.environ.get("DYD_METADATA_URI"))

    weather = attr.ib()
    hvac = attr.ib()

    # local or distributed caching
    local_data_dir = attr.ib(default=None)

    def __attrs_post_init__(self):
        # first, post init class specification
        if self.local_cache and os.path.exists(self.local_cache):
            self.local_data_dir = attr.ib(
                default=os.path.join(self.local_cache, self.data_source_name)
            )
            self.local_meta_dir = attr.ib(
                default=os.path.join(self.local_data_dir, "meta")
            )
            # for local cache save files on local machine
            os.makedirs(self.local_data_dir, exist_ok=True)
            os.makedirs(self.local_meta_dir, exist_ok=True)

    def get_data(self, tstat_sim_config):
        # first cast to utc timestamp
        # DYD uses UTC
        start_utc = pd.to_datetime(
            tstat_sim_config["start_utc"], utc=True, infer_datetime_format=True
        )
        end_utc = pd.to_datetime(
            tstat_sim_config["end_utc"], utc=True, infer_datetime_format=True
        )
        # check for invalid start/end combination
        invalid = tstat_sim_config[
            tstat_sim_config["end_utc"] <= tstat_sim_config["start_utc"]
        ]

        if not invalid.empty:
            raise ValueError(
                "tstat_sim_config contains invalid start_utc >= end_utc."
            )

        # supporting cross year simulations would require loading both years
        if np.any(end_utc.dt.year != start_utc.dt.year):
            raise ValueError("start_utc must be in same year as end_utc.")

        years_supported = [2016, 2017, 2018, 2019]
        if np.any(~start_utc.dt.year.isin(years_supported)):
            raise ValueError(
                f"start_utc must be in supported years: {years_supported}"
            )

        # HVAC and weather data are stored in same files in DYD
        # DYDHVACClient performs read and feeds to weather.from_dyd_hvac()
        self.hvac.get_data(tstat_sim_config)
        self.weather.get_data(
            tstat_sim_config, self.hvac.weather_data,
        )

        # send back full data periods to hypervisor
        return self.hvac.full_data_periods, self.weather.full_data_periods

    def get_metadata(self):
        return pd.read_csv(self.meta_gs_uri)
