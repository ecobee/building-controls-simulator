# created by Tom Stesco tom.s@ecobee.com

import logging
import os
from abc import ABC, abstractmethod

import attr
import pandas as pd
import numpy as np

from BuildingControlsSimulator.DataClients.DataSpec import (
    Internal,
    convert_spec,
)
from BuildingControlsSimulator.DataClients.DataStates import CHANNELS
from BuildingControlsSimulator.DataClients.DataSource import DataSource


logger = logging.getLogger(__name__)


@attr.s(kw_only=True)
class LocalSource(DataSource):

    source_name = attr.ib(default="local")
    local_cache = attr.ib()
    data_spec = attr.ib()
    file_extension = attr.ib(default=None)

    def __attrs_post_init__(self):
        """Infer the file_extension from local_cache supplied"""
        if os.path.isdir(self.local_cache_source):

            # find file extension
            extensions = []
            for _fname in os.listdir(self.local_cache_source):
                _ext = ".".join(_fname.split(".")[1:])
                if _ext not in extensions:
                    extensions.append(_ext)

            if len(extensions) == 0:
                raise ValueError(f"{self.local_cache_source} contains no data files.")
            elif len(extensions) == 1:
                self.file_extension = extensions[0]
            elif len(extensions) > 1:
                raise ValueError(
                    f"{self.local_cache_source} contains more than one file"
                    + f" extension type, extensions: {extensions}."
                )

        else:
            raise ValueError(
                f"{self.local_cache_source} is not a directory or does not exist."
            )

    def get_data(self, sim_config):
        """Get local cache"""
        local_cache_file = self.get_local_cache_file(
            identifier=sim_config["identifier"]
        )
        _data = self.get_local_cache(local_cache_file)
        _data = self.drop_unused_columns(_data=_data)
        _data = convert_spec(
            df=_data, src_spec=self.data_spec, dest_spec=Internal(), copy=False, src_nullable=True, dest_nullable=True
        )
        return _data
