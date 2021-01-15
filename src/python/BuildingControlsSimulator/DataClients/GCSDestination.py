# created by Tom Stesco tom.s@ecobee.com

import os
import logging
from abc import ABC, abstractmethod

import attr
import pandas as pd
import numpy as np
import gcsfs

from BuildingControlsSimulator.DataClients.DataStates import CHANNELS
from BuildingControlsSimulator.DataClients.DataDestination import (
    DataDestination,
)
from BuildingControlsSimulator.DataClients.DataSpec import (
    convert_spec,
)


logger = logging.getLogger(__name__)
# gcsfs DEBUG logging prints raw data bytes and is too verbose
gcsfs_logger = logging.getLogger("gcsfs")
gcsfs_logger.setLevel(logging.WARN)


@attr.s(kw_only=True)
class GCSDestination(DataDestination):

    # TODO: add validators
    gcp_project = attr.ib(default=None)
    gcs_uri_base = attr.ib(default=None)
    gcs_token = attr.ib(default=os.environ.get("GOOGLE_APPLICATION_CREDENTIALS"))

    def put_data(self, df, sim_name, src_spec):
        _df = convert_spec(
            df=df, src_spec=src_spec, dest_spec=self.data_spec, copy=True
        )
        local_cache_file = self.get_local_cache_file(sim_name)
        self.put_local_cache(_df, local_cache_file)
        gcs_uri = self.get_gcs_uri(sim_name=sim_name)
        self.put_gcs(_df, gcs_uri)

    def get_gcs_uri(self, sim_name):
        return os.path.join(self.gcs_uri_base, self.get_file_name(sim_name=sim_name))

    def put_gcs(self, df, gcs_uri):
        if gcs_uri:
            _fs = gcsfs.GCSFileSystem(
                project=self.gcp_project,
                token=self.gcs_token,
                access="read_write",
            )
            with _fs.open(gcs_uri, "wb") as _file:
                self.write_data_by_extension(df, _file, gcs_uri=gcs_uri)
        else:
            logger.error("put_gcs: gcs_uri is None.")
