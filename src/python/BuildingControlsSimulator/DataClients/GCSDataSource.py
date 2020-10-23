# created by Tom Stesco tom.s@ecobee.com

import logging
import os
import tempfile
from abc import ABC, abstractmethod

import attr
import pandas as pd
import numpy as np
import gcsfs
from google.cloud import storage

from BuildingControlsSimulator.DataClients.DataSource import DataSource
from BuildingControlsSimulator.DataClients.DataSpec import Internal
from BuildingControlsSimulator.DataClients.DataStates import CHANNELS

logger = logging.getLogger(__name__)


@attr.s(kw_only=True)
class GCSDataSource(DataSource, ABC):

    # TODO: add validators
    gcs_cache = attr.ib(default=None)
    gcp_project = attr.ib(default=None)
    gcs_uri_base = attr.ib(default=None)
    gcs_token = attr.ib(
        default=os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
    )

    def get_data(self, sim_config):

        # first check if file in local cache
        local_cache_path = self.get_local_cache_path(sim_config["identifier"])
        _data = self.get_local_cache(local_cache_path)
        if _data.empty:
            _data = self.get_gcs_cache(sim_config, local_cache_path)

        _data = self.convert_to_internal(_data=_data)
        return _data

    @abstractmethod
    def get_gcs_uri(self, sim_config):
        """This is implemented in the specialized source class"""
        pass

    def get_gcs_cache(self, sim_config, local_cache_path):
        if not self.gcs_uri_base:
            raise ValueError(
                f"gcs_uri_base={self.gcs_uri_base} is unset. "
                + "Set env variable for specific source, e.g. DYD_GCS_URI_BASE"
            )

        if not sim_config["identifier"]:
            raise ValueError(
                f"Invalid sim_config: sim_config[identifier]={sim_config['identifier']}"
            )

        gcs_uri = self.get_gcs_uri(sim_config)

        if local_cache_path:
            if os.path.isdir(os.path.dirname(local_cache_path)):
                client = storage.Client(project=self.gcp_project)
                with open(local_cache_path) as _file:
                    try:
                        client.download_blob_to_file(gcs_uri, _file)
                        _df = self.read_data_by_extension(_file)

                    except FileNotFoundError:
                        # file not found in DYD
                        logging.error(
                            (
                                f"File: {gcs_uri}",
                                " not found in gcs cache dataset.",
                            )
                        )
                        _df = self.get_empty_df()
            else:
                logger.error(
                    "GCSDataSource received invalid directory: "
                    + f"local_cache={self.local_cache}"
                )
        else:
            logger.info(
                "GCSDataSource received no local_cache. Proceeding without caching."
            )
            _fs = gcsfs.GCSFileSystem(
                project=self.gcp_project,
                token=self.gcs_token,
                access="read_only",
            )
            try:
                with _fs.open(gcs_uri) as _file:
                    _df = self.read_data_by_extension(_file)

            except FileNotFoundError:
                # file not found in DYD
                logging.error(
                    (
                        f"File: {gcs_uri}",
                        " not found in gcs cache dataset.",
                    )
                )
                _df = self.get_empty_df()

        return _df
