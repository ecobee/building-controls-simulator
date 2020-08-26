# created by Tom Stesco tom.s@ecobee.com

import os
import logging

import pandas as pd
import attr
import numpy as np

# from google.cloud import storage

from BuildingControlsSimulator.DataClients.DataClient import DataClient
from BuildingControlsSimulator.DataClients.DataClient import GCSDataSource

# from BuildingControlsSimulator.DataClients.DataSpec import DYD

logger = logging.getLogger(__name__)


@attr.s(kw_only=True)
class DYDClient(DataClient):
    """Client for DYD data.
    DYD is implemented as a GCS hosted cache.
    """

    data_source_name = attr.ib(default="dyd")
    meta_gs_uri = attr.ib(default=os.environ.get("DYD_METADATA_URI"))
    gcs_file_extension = attr.ib(default="csv.zip")
    gcs_uri_base = attr.ib(default=None)

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

        # self.data_source = GCSDataSource(spec=DYDSpec)

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
        # DYDHVACSource performs read and feeds to weather.from_dyd_hvac()
        self.data = GCSDataSource.get_data(tstat_sim_config)
        self.weather.get_data(
            tstat_sim_config, self.hvac.weather_data,
        )

    def get_metadata(self):
        return pd.read_csv(self.meta_gs_uri).drop_duplicates(
            subset=["Identifier"]
        )

    def get_gcs_uri(self, tstat_sim_config):
        tstat_sim_config = tstat_sim_config.reset_index()
        tstat_sim_config["gcs_uri"] = (
            self.gcs_uri_base
            + "/"
            + tstat_sim_config["start_utc"].dt.year.astype(str)
            + "/"
            + tstat_sim_config["identifier"]
            + "."
            + self.gcs_file_extension
        )
        tstat_sim_config = tstat_sim_config.set_index("identifier")
        return tstat_sim_config

    def get_full_data_periods(self, df):
        # if df has no records then there are no full_data_periods
        full_data_periods = []
        if len(df) > 0:
            df = df.sort_values("datetime", ascending=True)
            # drop records that are incomplete
            df = df[~df["HvacMode"].isnull()].reset_index()

            diffs = df[self.datetime_column].diff()

            # check for missing records
            missing_start_idx = diffs[
                diffs > pd.to_timedelta("5M")
            ].index.to_list()

            missing_end_idx = [idx - 1 for idx in missing_start_idx] + [
                len(df) - 1
            ]
            missing_start_idx = [0] + missing_start_idx
            # ensoure ascending before zip
            missing_start_idx.sort()
            missing_end_idx.sort()

            full_data_periods = list(
                zip(
                    pd.to_datetime(
                        df.datetime[missing_start_idx].values, utc=True
                    ),
                    pd.to_datetime(
                        df.datetime[missing_end_idx].values, utc=True
                    ),
                )
            )

        return full_data_periods
