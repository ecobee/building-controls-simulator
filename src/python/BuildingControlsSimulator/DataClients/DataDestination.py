# created by Tom Stesco tom.s@ecobee.com

import os
import logging
from abc import ABC, abstractmethod
import pkg_resources

import attr
import pandas as pd
import numpy as np

from BuildingControlsSimulator.DataClients.DataSpec import (
    Internal,
    DonateYourDataSpec,
    FlatFilesSpec,
)

logger = logging.getLogger(__name__)


@attr.s(kw_only=True)
class DataDestination(ABC):

    file_extension = attr.ib(default="parquet.gzip")
    compression = attr.ib(default="gzip")
    data_spec = attr.ib()
    local_cache = attr.ib(default=None)
    data = attr.ib(factory=dict)
    source_name = attr.ib(default=None)
    operator_name = attr.ib(default="output")

    @abstractmethod
    def put_data(self, df, sim_name):
        pass

    def make_data_directories(self):
        os.makedirs(
            os.path.join(
                self.local_cache,
                self.operator_name,
                self.source_name,
            ),
            exist_ok=True,
        )

    def get_file_name(self, sim_name):
        # sim_name may contain . character, replace this safely
        safe_sim_name = sim_name.replace(".", "_")
        return f"{safe_sim_name}.{self.file_extension}"

    def get_local_cache_file(self, sim_name):
        if self.local_cache:
            return os.path.join(
                self.local_cache,
                self.operator_name,
                self.get_file_name(sim_name),
            )
        else:
            logger.info("No local_cache provided. To enable set env LOCAL_CACHE_DIR.")
            return None

    def put_local_cache(self, df, local_cache_file):
        if local_cache_file and os.path.exists(os.path.dirname(local_cache_file)):
            self.write_data_by_extension(df, local_cache_file)
        else:
            logger.error(f"local_cache_file: {local_cache_file} does not exist.")

    def write_data_by_extension(
        self,
        df,
        filepath_or_buffer,
        data_spec=None,
        file_extension=None,
        gcs_uri=None,
    ):
        """When using a buffer of bytes the compression cannot be inferred."""

        # allow for overriding
        if not data_spec:
            data_spec = self.data_spec

        # check that filepath_or_buffer matches file_extension
        # default to filepath_or_buffer overriding
        if not gcs_uri:
            fpath_file_extension = os.path.basename(filepath_or_buffer).split(".", 1)[1]
        else:
            fpath_file_extension = os.path.basename(gcs_uri).split(".", 1)[1]

        if not file_extension:
            file_extension = self.file_extension
            if file_extension != fpath_file_extension:
                logger.warn(
                    f"Expected DataDestination file extension: {file_extension}"
                )
                file_extension = fpath_file_extension

        if not fpath_file_extension:
            if file_extension:
                filepath_or_buffer = filepath_or_buffer + "." + file_extension
            else:
                raise ValueError(
                    f"filepath_or_buffer: {filepath_or_buffer} contains no file extension."
                    + f" Default file_extension: {file_extension}."
                )

        # use human readable column names
        if isinstance(data_spec, Internal):
            # if modifing df for export need a copy
            _df = df.copy(deep=True)
            _df.columns = [data_spec.full.spec[_col]["name"] for _col in _df.columns]
        else:
            _df = df

        DataDestination.write_data_static(_df, filepath_or_buffer, file_extension)

    @staticmethod
    def write_data_static(_df, filepath_or_buffer, file_extension="parquet.gzip"):
        """When using a buffer of bytes the compression cannot be inferred."""

        logger.info(f"Storing simulation ouput at: {filepath_or_buffer}")
        if file_extension.startswith("parquet"):
            # note: parquet requires string column names
            _df.to_parquet(
                filepath_or_buffer,
                compression="gzip",
                index=False,
            )
        elif file_extension == "csv":
            _df.to_csv(
                filepath_or_buffer,
                compression=None,
                index=False,
            )
        elif file_extension == "csv.zip":
            _df.to_csv(
                filepath_or_buffer,
                compression="zip",
                index=False,
            )
        elif file_extension in ["csv.gzip", "csv.gz"]:
            _df.to_csv(
                filepath_or_buffer,
                compression="gzip",
                index=False,
            )
        else:
            logger.error(f"Unsupported destination file extension: {file_extension}")
