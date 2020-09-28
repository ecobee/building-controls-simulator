# created by Tom Stesco tom.s@ecobee.com

import logging

from abc import ABC, abstractmethod

import attr
import pandas as pd
import numpy as np

from BuildingControlsSimulator.DataClients.DataSource import DataSource
from BuildingControlsSimulator.DataClients.DataSpec import Internal

logger = logging.getLogger(__name__)


@attr.s(kw_only=True)
class GCSDataSource(DataSource, ABC):

    gcs_cache = attr.ib(default=None)
    gcp_project = attr.ib(default=None)
    gcs_uri_base = attr.ib(default=None)
    gcs_uri = attr.ib(default=None)

    def get_data(self, sim_config):

        # first check if file in local cache
        local_cache_path = self.get_local_cache_path(sim_config["identifier"])
        cache_df = self.get_local_cache(local_cache_path)

        if cache_df.empty:
            self.gcs_uri = self.get_gcs_uri(sim_config)
            cache_df = self.get_gcs_cache(self.gcs_uri)
            if not cache_df.empty:
                # if downloaded the data file put it in local cache
                self.put_cache(cache_df, local_cache_path)
        # convert to input format spec
        # do dtype conversion after read, it sometimes fails on read
        cache_df = cache_df.astype(
            self.data_spec.full.get_dtype_mapper(cache_df.columns)
        )

        # check cache contains all expected columns
        missing_cols = [
            c for c in self.data_spec.full.columns if c not in cache_df.columns
        ]
        if missing_cols:
            logging.error(
                "tstat: {} has _missing_ columns: {}".format(
                    identifier, missing_cols
                )
            )
            logging.error(
                "tstat: {} has columns: {}".format(
                    identifier, cache_df.columns
                )
            )

        # convert to internal spec
        cache_df = Internal.convert_to_internal(cache_df, self.data_spec.full)

        return cache_df

    @abstractmethod
    def get_gcs_uri(self, sim_config):
        pass

    def get_gcs_cache(self, gcs_uri):
        try:
            _df = pd.read_csv(gcs_uri, usecols=self.data_spec.full.columns,)
        except FileNotFoundError:
            # file not found in DYD
            logging.error(
                (f"File: {gcs_uri}", " not found in gcs cache dataset.",)
            )
            _df = self.get_empty_df()

        return _df
