# created by Tom Stesco tom.s@ecobee.com

import logging
import os
from abc import ABC, abstractmethod

import attr
import pandas as pd
import numpy as np
import gcsfs
from google.cloud import bigquery, exceptions
import pandas_gbq

from BuildingControlsSimulator.DataClients.DataSource import DataSource
from BuildingControlsSimulator.DataClients.DataSpec import (
    Internal,
    convert_spec,
)
from BuildingControlsSimulator.DataClients.DataStates import CHANNELS

logger = logging.getLogger(__name__)


@attr.s(kw_only=True)
class GBQDataSource(DataSource, ABC):

    # TODO: add validators
    gcp_project = attr.ib(default=None)
    gbq_table = attr.ib(default=None)
    gbq_token = attr.ib(default=os.environ.get("GOOGLE_APPLICATION_CREDENTIALS"))
    # data is written and read back using parquet.gzip format

    file_extension = attr.ib(default="parquet.gzip")

    def __attrs_post_init__(self):
        # replace . with _ in table name
        self.source_name = "GBQ_" + self.gbq_table.replace(".", "_")

    def get_data(self, sim_config):
        # first check if file in local cache
        local_cache_file = self.get_local_cache_file(
            identifier=sim_config["identifier"]
        )
        _data = self.get_local_cache(local_cache_file)
        if _data.empty:
            _data = self.get_gbq_data(sim_config, local_cache_file)
        _data = self.drop_unused_columns(_data=_data)
        _data = convert_spec(df=_data, src_spec=self.data_spec, dest_spec=Internal(), src_nullable=True, dest_nullable=True)
        return _data

    def get_gbq_data(self, sim_config, local_cache_file):
        if not self.gbq_table:
            raise ValueError(
                f"gbq_table={self.gbq_table} is unset. "
                + "Set env variable for specific source, e.g. FLATFILES_GBQ_TABLE"
            )

        if not sim_config["identifier"]:
            raise ValueError(
                f"Invalid sim_config: sim_config[identifier]={sim_config['identifier']}"
            )

        # query will get data for entire data set per ID so that the cache can
        # be built up correctly.
        columns_str = ", ".join(self.data_spec.full.columns)
        query_str = f"SELECT {columns_str}\n"
        query_str += f"FROM `{self.gbq_table}`\n"
        query_str += f"WHERE Identifier = '{sim_config['identifier']}'\n"
        # query_str += f"AND {self.data_spec.datetime_column} >= '{sim_config['start_utc']}'\n"
        # query_str += f"AND {self.data_spec.datetime_column} <= '{sim_config['end_utc']}'"

        # we will use pandas-gbq to read data to df
        # https://pandas-gbq.readthedocs.io/en/latest/
        # use_bqstorage_api=False
        # BigQuery Storage API allows downloading large (>125 MB) query results
        # more quickly at an increased cost. We are querying once per ID, which
        # should be no more than 50 MB.
        # max_results=1,000,000
        # 8760 * 12 = 105,120 records per thermostat-year
        # use max_results as guard to query accidentaly getting multiple datasets
        # there should never be 1,000,000 results for a single identifier

        _df = pandas_gbq.read_gbq(
            query=query_str,
            project_id=self.gcp_project,
            credentials=self.gbq_token,
            col_order=self.data_spec.full.columns,
            reauth=True,
            dialect="standard",
            max_results=1000000,
            use_bqstorage_api=False,
            dtypes={k: v["dtype"] for k, v in self.data_spec.full.spec.items()},
        )

        if _df.empty:
            logger.error(
                (
                    f"Identifier: {sim_config['identifier']}",
                    f" not found in GBQ table: {self.gbq_table}",
                )
            )

        if local_cache_file:
            if os.path.isdir(os.path.dirname(local_cache_file)):
                # store as gzip compressed parquet file
                _df.to_parquet(local_cache_file, compression="gzip", index=False)
        else:
            logger.info(
                "GCSDataSource received no local_cache. Proceeding without caching."
            )

        return _df
