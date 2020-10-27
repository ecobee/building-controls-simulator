# created by Tom Stesco tom.s@ecobee.com

import os
import logging
from abc import ABC, abstractmethod

import attr
import pandas as pd
import numpy as np

from BuildingControlsSimulator.DataClients.DataSpec import (
    convert_spec,
    get_dtype_mapper,
)
from BuildingControlsSimulator.DataClients.DataStates import CHANNELS

logger = logging.getLogger(__name__)


@attr.s(kw_only=True)
class DataSource(ABC):

    file_extension = attr.ib()
    data_spec = attr.ib()
    local_cache = attr.ib(default=None)
    data = attr.ib(factory=dict)
    source_name = attr.ib(default=None)
    operator_name = attr.ib(default="input")

    # Note: this should not be initialized in the base class because it causes
    # issues with the attrs initialization ordering
    @property
    def local_cache_source(self):
        if self.local_cache:
            return os.path.join(
                self.local_cache, self.operator_name, self.source_name
            )
        else:
            return None

    @abstractmethod
    def get_data(self, sim_config):
        pass

    def drop_unused_columns(self, _data):
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
        return _data.drop(axis="columns", columns=_all_null_columns)

    def get_local_cache_file(self, identifier):
        if self.local_cache:
            return os.path.join(
                self.local_cache_source,
                f"{identifier}.{self.file_extension}",
            )
        else:
            logger.info(
                "No local_cache provided. To enable set env LOCAL_CACHE_DIR."
            )
            return None

    def get_local_cache(self, local_cache_file):
        if local_cache_file and os.path.exists(local_cache_file):
            _df = self.read_data_by_extension(local_cache_file)
        else:
            _df = self.get_empty_df()

        return _df

    def get_empty_df(self):
        return pd.DataFrame([], columns=self.data_spec.full.columns)

    def read_data_by_extension(self, filepath_or_buffer, extension=None):
        """When using a buffer of bytes the compression cannot be inferred."""
        # override extension
        if not extension:
            extension = self.file_extension

        if extension.startswith("parquet"):
            # read_parquet does not take dtype info
            _df = pd.read_parquet(
                filepath_or_buffer,
                columns=self.data_spec.full.columns,
            )
        elif extension == "csv":
            # pandas cannot currently parse datetimes in read_csv
            # need to first remove from dtype map
            # see: https://github.com/pandas-dev/pandas/issues/26934
            _df = pd.read_csv(
                filepath_or_buffer,
                compression=None,
                usecols=self.data_spec.full.columns,
                dtype=get_dtype_mapper(
                    [
                        _col
                        for _col in self.data_spec.full.columns
                        if _col != self.data_spec.datetime_column
                    ],
                    self.data_spec,
                ),
            )
        elif extension == "csv.zip":
            _df = pd.read_csv(
                filepath_or_buffer,
                compression="zip",
                usecols=self.data_spec.full.columns,
                dtype=get_dtype_mapper(
                    [
                        _col
                        for _col in self.data_spec.full.columns
                        if _col != self.data_spec.datetime_column
                    ],
                    self.data_spec,
                ),
            )
        elif extension in ["csv.gzip", "csv.gz"]:
            _df = pd.read_csv(
                filepath_or_buffer,
                compression="gzip",
                usecols=self.data_spec.full.columns,
                dtype=get_dtype_mapper(
                    [
                        _col
                        for _col in self.data_spec.full.columns
                        if _col != self.data_spec.datetime_column
                    ],
                    self.data_spec,
                ),
            )
        else:
            _df = self.get_empty_df()

        return _df
