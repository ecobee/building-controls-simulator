# created by Tom Stesco tom.s@ecobee.com

import logging

import attr
import pandas as pd
import numpy as np

from BuildingControlsSimulator.DataClients.GCSDataSource import GCSDataSource
from BuildingControlsSimulator.DataClients.DataSpec import DonateYourDataSpec


@attr.s(kw_only=True)
class GCSDYDSource(GCSDataSource):

    data_spec = attr.ib(default=DonateYourDataSpec)
    file_extension = attr.ib(default="csv.zip")
    source_name = attr.ib(default="GCSDYD")

    def get_gcs_uri(self, sim_config):
        # first cast to utc timestamp
        # DYD uses UTC
        start_utc = pd.to_datetime(
            sim_config["start_utc"], utc=True, infer_datetime_format=True
        )
        end_utc = pd.to_datetime(
            sim_config["end_utc"], utc=True, infer_datetime_format=True
        )

        # supporting cross year simulations would require loading both years
        if np.any(end_utc.dt.year != start_utc.dt.year):
            raise ValueError("start_utc must be in same year as end_utc.")

        years_supported = [2016, 2017, 2018, 2019]
        if np.any(~start_utc.dt.year.isin(years_supported)):
            raise ValueError(
                f"start_utc must be in supported years: {years_supported}"
            )
        sim_config = sim_config.reset_index()
        sim_config["gcs_uri"] = (
            self.gcs_uri_base
            + "/"
            + sim_config["start_utc"].dt.year.astype("str")
            + "/"
            + sim_config["identifier"]
            + "."
            + self.file_extension
        )

        sim_config = sim_config.set_index("identifier")

        return sim_config
