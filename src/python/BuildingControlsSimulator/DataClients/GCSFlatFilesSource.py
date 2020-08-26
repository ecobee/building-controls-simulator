# created by Tom Stesco tom.s@ecobee.com

import logging

import attr
import pandas as pd
import numpy as np

from BuildingControlsSimulator.DataClients.GCSDataSource import GCSDataSource

from BuildingControlsSimulator.DataClients.DataSpec import FlatFilesSpec


@attr.s(kw_only=True)
class GCSFlatFilesSource(GCSDataSource):

    data_spec = attr.ib(default=FlatFilesSpec)
    file_extension = attr.ib(default="csv.gz")
    source_name = attr.ib(default="GCSFlatFiles")

    def get_gcs_uri(self, tstat_sim_config):
        tstat_sim_config = tstat_sim_config.reset_index()
        tstat_sim_config["gcs_uri"] = (
            self.gcs_uri_base
            + "/"
            + tstat_sim_config["identifier"]
            + "."
            + self.file_extension
        )

        tstat_sim_config = tstat_sim_config.set_index("identifier")

        return tstat_sim_config
