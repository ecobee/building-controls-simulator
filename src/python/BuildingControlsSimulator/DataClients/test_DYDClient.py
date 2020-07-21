# created by Tom Stesco tom.s@ecobee.com

import logging

import pytest
import pandas as pd
import pytz
import os

from BuildingControlsSimulator.DataClients.DYDClient import DYDClient
from BuildingControlsSimulator.DataClients.DYDHVACClient import DYDHVACClient
from BuildingControlsSimulator.DataClients.DYDWeatherClient import (
    DYDWeatherClient,
)


logger = logging.getLogger(__name__)


class TestDYDClient:
    @classmethod
    def setup_class(cls):
        # initialize with data to avoid pulling multiple times
        cls.dyd = DYDClient(
            hvac=DYDHVACClient(
                gcs_uri_base=os.environ.get("DYD_GCS_URI_BASE"),
                gcp_project=os.environ.get("GOOGLE_CLOUD_PROJECT"),
            ),
            weather=DYDWeatherClient(
                gcs_uri_base=os.environ.get("DYD_GCS_URI_BASE"),
                gcp_project=os.environ.get("GOOGLE_CLOUD_PROJECT"),
                nrel_dev_api_key=os.environ.get("NREL_DEV_API_KEY"),
                nrel_dev_email=os.environ.get("NREL_DEV_EMAIL"),
                archive_tmy3_meta=os.environ.get("ARCHIVE_TMY3_META"),
                archive_tmy3_data_dir=os.environ.get("ARCHIVE_TMY3_DATA_DIR"),
                ep_tmy3_cache_dir=os.environ.get("EP_TMY3_CACHE_DIR"),
                simulation_epw_dir=os.environ.get("SIMULATION_EPW_DIR"),
            ),
        )

        DYDClient.make_data_directories()

        cls.tstat_sim_config = DYDClient.make_tstat_sim_config(
            identifier=[
                "f2254479e14daf04089082d1cd9df53948f98f1e",  # missing data
                "2df6959cdf502c23f04f3155758d7b678af0c631",  # full
                "6e63291da5427ae87d34bb75022ee54ee3b1fc1a",  # file not found
            ],
            latitude=[33.481136, 33.481136, 33.481136],
            longitude=[-112.078232, -112.078232, -112.078232],
            start_utc=["2019-01-01", "2019-01-01", "2019-01-01"],
            end_utc=["2019-12-31", "2019-02-15", "2019-12-31"],
        )

        cls.dyd.get_data(tstat_sim_config=cls.tstat_sim_config)
        cls.tstat_sim_config["has_hvac_simulation_data"] = pd.Series(
            cls.dyd.hvac.has_simulation_data(
                cls.tstat_sim_config,
                full_data_periods=cls.dyd.hvac.full_data_periods,
            )
        )

        cls.tstat_sim_config["has_weather_simulation_data"] = pd.Series(
            cls.dyd.weather.has_simulation_data(
                cls.tstat_sim_config,
                full_data_periods=cls.dyd.weather.full_data_periods,
            )
        )

    @classmethod
    def teardown_class(cls):
        """ teardown any state that was previously setup with a call to
        setup_class.
        """
        pass

    def test_has_simulation_data(self):
        # test HVAC data returns dict of non-empty pd.DataFrame
        for identifier, tstat in self.tstat_sim_config.iterrows():
            assert isinstance(self.dyd.hvac.data[identifier], pd.DataFrame)
            if tstat.has_hvac_simulation_data:
                assert self.dyd.hvac.data[identifier].empty is False

    def test_read_epw(self):
        # read back cached filled epw files
        for identifier, tstat in self.tstat_sim_config.iterrows():
            if tstat["has_weather_simulation_data"]:
                data, meta, meta_lines = self.dyd.weather.read_epw(
                    self.dyd.weather.epw_fpaths[identifier]
                )
                assert not data.empty
                assert all(
                    data.columns
                    == self.dyd.weather.epw_columns
                    + [self.dyd.weather.datetime_column]
                )

    def test_data_utc(self):

        for identifier, tstat in self.tstat_sim_config.iterrows():
            assert (
                self.dyd.hvac.data[identifier][
                    self.dyd.hvac.datetime_column
                ].dt.tz
                == pytz.utc
            )
            assert (
                self.dyd.weather.data[identifier][
                    self.dyd.weather.datetime_column
                ].dt.tz
                == pytz.utc
            )
