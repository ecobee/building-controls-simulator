# created by Tom Stesco tom.s@ecobee.com

import logging

import attr
import pandas as pd
import numpy as np
import gcsfs

from BuildingControlsSimulator.DataClients.GCSDataSource import GCSDataSource
from BuildingControlsSimulator.DataClients.DataSpec import DonateYourDataSpec


logger = logging.getLogger(__name__)
gcsfs_logger = logging.getLogger("gcsfs")
gcsfs_logger.setLevel(logging.WARN)


@attr.s(kw_only=True)
class GCSDYDSource(GCSDataSource):

    data_spec = attr.ib(factory=DonateYourDataSpec)
    file_extension = attr.ib(default="csv.zip")
    source_name = attr.ib(default="GCSDYD")
    meta_gcs_uri = attr.ib(default=None)

    def get_metadata(self):
        if self.meta_gcs_uri:
            _fs = gcsfs.GCSFileSystem(
                project=self.gcp_project,
                token=self.gcs_token,
                access="read_only",
            )
            with _fs.open(self.meta_gcs_uri) as _file:
                _df = pd.read_csv(_file).drop_duplicates(subset=["Identifier"])

        else:
            raise ValueError("Must supply `meta_gs_uri` to dataclient.")

        return _df

    def get_gcs_uri(self, sim_config):
        # first cast to utc timestamp
        # DYD uses UTC
        start_utc = pd.to_datetime(
            sim_config["start_utc"], utc=True, infer_datetime_format=True
        )
        end_utc = pd.to_datetime(
            sim_config["end_utc"], utc=True, infer_datetime_format=True
        )

        if isinstance(start_utc, pd.Timestamp):
            start_year = start_utc.year
        else:
            start_year = start_utc.dt.year

        if isinstance(end_utc, pd.Timestamp):
            end_year = end_utc.year
        else:
            end_year = end_utc.dt.year

        # supporting cross year simulations would require loading both years
        if np.any(end_year != start_year):
            raise ValueError("start_utc must be in same year as end_utc.")

        years_supported = [2016, 2017, 2018, 2019]
        if start_year not in years_supported:
            raise ValueError(
                f"start_utc must be in supported years: {years_supported}"
            )

        return (
            self.gcs_uri_base
            + "/"
            + str(start_year)
            + "/"
            + sim_config["identifier"]
            + "."
            + self.file_extension
        )
