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

    def get_data(self, tstat_sim_config):

        # first get GCS URI
        tstat_sim_config = self.get_gcs_uri(tstat_sim_config)
        cache_dict = {}
        for identifier, tstat in tstat_sim_config.iterrows():
            # first check if file in local cache
            cache_dict[identifier] = self.get_local_cache(identifier)
            if cache_dict[identifier].empty:
                cache_dict[identifier] = self.get_gcs_cache(tstat)
                if not cache_dict[identifier].empty:
                    # if downloaded the data file put it in local cache
                    self.put_cache(cache_dict[identifier], identifier)
            # convert to input format spec
            # do dtype conversion after read, it sometimes fails on read
            cache_dict[identifier] = cache_dict[identifier].astype(
                self.data_spec.full.get_dtype_mapper(
                    cache_dict[identifier].columns
                )
            )

            # check cache contains all expected columns
            missing_cols = [
                c
                for c in self.data_spec.full.columns
                if c not in cache_dict[identifier].columns
            ]
            if missing_cols:
                logging.error(
                    "tstat: {} has _missing_ columns: {}".format(
                        identifier, missing_cols
                    )
                )
                logging.error(
                    "tstat: {} has columns: {}".format(
                        identifier, cache_dict[identifier].columns
                    )
                )

            # convert to internal spec
            cache_dict[identifier] = Internal.convert_to_internal(
                cache_dict[identifier], self.data_spec.full
            )

        return cache_dict

    @abstractmethod
    def get_gcs_uri(self, tstat_sim_config):
        pass

    def get_gcs_cache(self, tstat):
        try:
            _df = pd.read_csv(
                tstat.gcs_uri, usecols=self.data_spec.full.columns,
            )
        except FileNotFoundError:
            # file not found in DYD
            logging.error(
                (f"File: {tstat.gcs_uri}", " not found in gcs cache dataset.",)
            )
            _df = self.get_empty_df()

        return _df
