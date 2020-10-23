# created by Tom Stesco tom.s@ecobee.com

import os
import logging
from abc import ABC, abstractmethod

import attr
import pandas as pd
import numpy as np

from BuildingControlsSimulator.DataClients.DataSpec import Internal
from BuildingControlsSimulator.DataClients.DataStates import CHANNELS

logger = logging.getLogger(__name__)


@attr.s(kw_only=True)
class DataSource(ABC):

    file_extension = attr.ib()
    data_spec = attr.ib()
    local_cache = attr.ib(default=None)
    data = attr.ib(factory=dict)
    source_name = attr.ib(default=None)

    @abstractmethod
    def get_data(self, sim_config):
        pass

    def convert_to_internal(self, _data):
        # check cache contains all expected columns
        missing_cols = [
            c for c in self.data_spec.full.columns if c not in _data.columns
        ]
        if missing_cols:
            logging.error(
                "tstat: {} has _missing_ columns: {}".format(
                    sim_config["identifier"], missing_cols
                )
            )
            logging.error(
                "tstat: {} has columns: {}".format(
                    sim_config["identifier"], _data.columns
                )
            )

        # drop all null remote sensor columns
        _all_null_columns = [
            _col
            for _col in _data.columns
            if (
                _data[_col].isnull().all()
                and self.data_spec.full.spec[_col]["channel"]
                == CHANNELS.REMOTE_SENSOR
            )
        ]
        _data = _data.drop(axis="columns", columns=_all_null_columns)
        # convert to input format spec
        # do dtype conversion after read, it sometimes fails on read
        _data = _data.astype(
            self.data_spec.full.get_dtype_mapper(_data.columns)
        )

        # convert to internal spec
        _data = Internal.convert_to_internal(_data, self.data_spec.full)
        return _data

    def get_local_cache_path(self, identifier):
        if self.local_cache:
            return os.path.join(
                self.local_cache,
                self.source_name,
                "{}.{}".format(identifier, self.file_extension),
            )
        else:
            logging.info("No local_cache provided. Set env LOCAL_CACHE_DIR.")
            return None

    def get_local_cache(self, local_cache_path):
        if local_cache_path and os.path.exists(local_cache_path):
            _df = pd.read_csv(
                local_cache_path,
                usecols=self.data_spec.full.columns,
            )
        else:
            _df = self.get_empty_df()

        return _df

    def get_empty_df(self):
        return pd.DataFrame([], columns=self.data_spec.full.columns)

    def read_data_by_extension(self, filepath_or_buffer):
        """When using a buffer of bytes the compression cannot be inferred."""
        if self.file_extension.startswith("parquet"):
            _df = pd.read_parquet(
                filepath_or_buffer,
                columns=self.data_spec.full.columns,
            )
        elif self.file_extension == "csv":
            _df = pd.read_csv(
                filepath_or_buffer,
                compression=None,
                usecols=self.data_spec.full.columns,
            )
        elif self.file_extension == "csv.zip":
            _df = pd.read_csv(
                filepath_or_buffer,
                compression="zip",
                usecols=self.data_spec.full.columns,
            )
        elif self.file_extension in ["csv.gzip", "csv.gz"]:
            _df = pd.read_csv(
                filepath_or_buffer,
                compression="gzip",
                usecols=self.data_spec.full.columns,
            )
        else:
            _df = self.get_empty_df()

        return _df
