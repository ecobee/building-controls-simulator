# created by Tom Stesco tom.s@ecobee.com

import logging
import os
from abc import ABC, abstractmethod

import attr
import pandas as pd
import numpy as np

from BuildingControlsSimulator.DataClients.DataSpec import Internal
from BuildingControlsSimulator.DataClients.DataStates import CHANNELS
from BuildingControlsSimulator.DataClients.DataSource import DataSource


logger = logging.getLogger(__name__)


@attr.s(kw_only=True)
class LocalSource(DataSource):

    source_name = attr.ib(default="local")
    local_cache = attr.ib()
    local_cache_data_dir = attr.ib(default=None)
    data_spec = attr.ib()
    file_extension = attr.ib(default=None)

    def __attrs_post_init__(self):
        """Infer the file_extension from local_cache supplied"""
        self.local_cache_data_dir = os.path.join(
            self.local_cache, self.source_name
        )
        if os.path.isdir(self.local_cache_data_dir):

            # find file extension
            extensions = []
            for _fname in os.listdir(self.local_cache_data_dir):
                _ext = ".".join(_fname.split(".")[1:])
                if _ext not in extensions:
                    extensions.append(_ext)

            if len(extensions) == 0:
                raise ValueError(
                    f"{self.local_cache_data_dir} contains no data files."
                )
            elif len(extensions) == 1:
                self.file_extension = extensions[0]
            elif len(extensions) > 1:
                ValueError(
                    f"{self.local_cache_data_dir} contains more than one file"
                    + f" extension type, extensions: {extensions}."
                )

        else:
            raise ValueError(
                f"{self.local_cache_data_dir} is not a directory or does not exist."
            )

    def get_data(self, sim_config):
        """Get local cache"""
        _data = self.get_local_cache(
            local_cache_path=self.get_local_cache_path(
                identifier=sim_config["identifier"]
            )
        )
        _data = self.convert_to_internal(_data=_data)
        return _data
