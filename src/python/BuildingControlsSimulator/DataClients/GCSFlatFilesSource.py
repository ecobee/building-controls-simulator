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

    def get_gcs_uri(self, sim_config):
        sim_config = sim_config.reset_index()
        sim_config["gcs_uri"] = (
            self.gcs_uri_base
            + "/"
            + sim_config["identifier"]
            + "."
            + self.file_extension
        )

        sim_config = sim_config.set_index("identifier")

        return sim_config
