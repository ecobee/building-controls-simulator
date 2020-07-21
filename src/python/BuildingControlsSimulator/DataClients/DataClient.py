# created by Tom Stesco tom.s@ecobee.com
import os
import logging
from abc import ABC, abstractmethod

import attr
import pandas as pd

logger = logging.getLogger(__name__)


@attr.s(kw_only=True)
class DataClient(ABC):

    local_cache = attr.ib(default=None)
    gcs_cache = attr.ib(default=None)
    tstat_sim_config_columns = attr.ib(
        default=[
            "identifiers",
            "start_utc",
            "end_utc",
            "latitude",
            "longitude",
        ]
    )

    @abstractmethod
    def get_data(self, tstat_sim_config):
        pass

    @staticmethod
    def make_tstat_sim_config(
        identifier, latitude, longitude, start_utc, end_utc
    ):
        return pd.DataFrame.from_dict(
            {
                "identifier": identifier,
                "latitude": latitude,
                "longitude": longitude,
                "start_utc": pd.to_datetime(start_utc, utc=True),
                "end_utc": pd.to_datetime(end_utc, utc=True),
            }
        ).set_index("identifier")

    @staticmethod
    def make_data_directories():
        os.makedirs(os.environ.get("WEATHER_DIR"), exist_ok=True)
        os.makedirs(os.environ.get("ARCHIVE_TMY3_DATA_DIR"), exist_ok=True)
        os.makedirs(os.environ.get("EP_TMY3_CACHE_DIR"), exist_ok=True)
        os.makedirs(os.environ.get("SIMULATION_EPW_DIR"), exist_ok=True)
        os.makedirs(os.environ.get("FMU_DIR"), exist_ok=True)
        os.makedirs(os.environ.get("IDF_DIR"), exist_ok=True)
