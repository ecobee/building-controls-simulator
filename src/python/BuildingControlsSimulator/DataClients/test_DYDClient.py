# created by Tom Stesco tom.s@ecobee.com
import logging
import os

import pytest
import pandas as pd
import pytz

from BuildingControlsSimulator.DataClients.DataClient import DataClient
from BuildingControlsSimulator.DataClients.GCSDYDSource import GCSDYDSource
from BuildingControlsSimulator.DataClients.DataSpec import EnergyPlusWeather


logger = logging.getLogger(__name__)


class TestFlatFilesClient:
    @classmethod
    def setup_class(cls):
        # initialize with data to avoid pulling multiple times
        cls.dc = DataClient(
            sources=[
                GCSDYDSource(
                    gcp_project=os.environ.get("GOOGLE_CLOUD_PROJECT"),
                    gcs_uri_base=os.environ.get("DYD_GCS_URI_BASE"),
                )
            ],
            nrel_dev_api_key=os.environ.get("NREL_DEV_API_KEY"),
            nrel_dev_email=os.environ.get("NREL_DEV_EMAIL"),
            archive_tmy3_meta=os.environ.get("ARCHIVE_TMY3_META"),
            archive_tmy3_data_dir=os.environ.get("ARCHIVE_TMY3_DATA_DIR"),
            ep_tmy3_cache_dir=os.environ.get("EP_TMY3_CACHE_DIR"),
            simulation_epw_dir=os.environ.get("SIMULATION_EPW_DIR"),
        )

        cls.sim_config = cls.dc.make_sim_config(
            identifier=[
                "f2254479e14daf04089082d1cd9df53948f98f1e",  # missing thermostat_temperature data
                "2df6959cdf502c23f04f3155758d7b678af0c631",  # has full data periods
                "6e63291da5427ae87d34bb75022ee54ee3b1fc1a",  # file not found
            ],
            latitude=33.481136,
            longitude=-112.078232,
            start_utc="2019-01-01",
            end_utc="2019-12-31",
            min_sim_period="7D",
            min_chunk_period="30D",
        )

        cls.dc.get_data(sim_config=cls.sim_config)
        cls.sim_hvac_data, cls.sim_weather_data = cls.dc.get_simulation_data(
            cls.sim_config,
        )

    @classmethod
    def teardown_class(cls):
        """ teardown any state that was previously setup with a call to
        setup_class.
        """
        pass

    def test_get_simulation_data(self):
        # test HVAC data returns dict of non-empty pd.DataFrame
        for identifier, tstat in self.sim_config.iterrows():
            assert all(
                [
                    isinstance(p, pd.DataFrame)
                    for p in self.sim_hvac_data[identifier]
                ]
            )
            assert all(
                [
                    isinstance(p, pd.DataFrame)
                    for p in self.sim_weather_data[identifier]
                ]
            )

    def test_read_epw(self):
        # read back cached filled epw files
        for identifier, tstat in self.sim_config.iterrows():
            if identifier in self.dc.weather.keys():
                data, meta, meta_lines = self.dc.weather[identifier].read_epw(
                    self.dc.weather[identifier].epw_fpath
                )
                assert not data.empty
                assert all(
                    data.columns
                    == self.dc.weather[identifier].epw_columns
                    + [EnergyPlusWeather.datetime_column]
                )
            else:
                assert self.dc.weather[identifier].data.empty

    def test_data_utc(self):

        for identifier, tstat in self.sim_config.iterrows():
            if not self.dc.hvac[identifier].data.empty:
                assert (
                    self.dc.hvac[identifier]
                    .data[self.dc.hvac[identifier].spec.datetime_column]
                    .dt.tz
                    == pytz.utc
                )
            if not self.dc.weather[identifier].data.empty:
                assert (
                    self.dc.weather[identifier]
                    .data[self.dc.weather[identifier].spec.datetime_column]
                    .dt.tz
                    == pytz.utc
                )
