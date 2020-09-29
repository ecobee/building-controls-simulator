# created by Tom Stesco tom.s@ecobee.com
import logging
import os
import copy

import pytest
import pandas as pd
import pytz

from BuildingControlsSimulator.Simulator.Config import Config
from BuildingControlsSimulator.DataClients.DataClient import DataClient
from BuildingControlsSimulator.DataClients.GCSDYDSource import GCSDYDSource
from BuildingControlsSimulator.DataClients.DataSpec import EnergyPlusWeather
from BuildingControlsSimulator.DataClients.DataStates import STATES

logger = logging.getLogger(__name__)


class TestFlatFilesClient:
    @classmethod
    def setup_class(cls):
        # initialize with data to avoid pulling multiple times
        cls.sim_config = Config.make_sim_config(
            identifier=[
                "f2254479e14daf04089082d1cd9df53948f98f1e",  # missing thermostat_temperature data
                "2df6959cdf502c23f04f3155758d7b678af0c631",  # has full data periods
                "6e63291da5427ae87d34bb75022ee54ee3b1fc1a",  # file not found
            ],
            latitude=33.481136,
            longitude=-112.078232,
            start_utc="2018-01-01",
            end_utc="2018-12-31",
            min_sim_period="7D",
            min_chunk_period="30D",
            step_size_minutes=5,
        )

        cls.data_clients = []
        cls.data_client = DataClient(
            source=GCSDYDSource(
                gcp_project=os.environ.get("GOOGLE_CLOUD_PROJECT"),
                gcs_uri_base=os.environ.get("DYD_GCS_URI_BASE"),
            ),
            nrel_dev_api_key=os.environ.get("NREL_DEV_API_KEY"),
            nrel_dev_email=os.environ.get("NREL_DEV_EMAIL"),
            archive_tmy3_dir=os.environ.get("ARCHIVE_TMY3_DIR"),
            archive_tmy3_meta=os.environ.get("ARCHIVE_TMY3_META"),
            archive_tmy3_data_dir=os.environ.get("ARCHIVE_TMY3_DATA_DIR"),
            ep_tmy3_cache_dir=os.environ.get("EP_TMY3_CACHE_DIR"),
            simulation_epw_dir=os.environ.get("SIMULATION_EPW_DIR"),
        )

        for _idx, _sim_config in cls.sim_config.iterrows():
            dc = copy.deepcopy(cls.data_client)
            dc.sim_config = _sim_config

            dc.get_data()

            cls.data_clients.append(dc)

    @classmethod
    def teardown_class(cls):
        """ teardown any state that was previously setup with a call to
        setup_class.
        """
        pass

    def test_get_simulation_data(self):
        # test HVAC data returns dict of non-empty pd.DataFrame
        for dc in self.data_clients:
            assert all(
                [isinstance(_df, pd.DataFrame) for _df in dc.hvac.sim_data]
            )
            assert all(
                [isinstance(_df, pd.DataFrame) for _df in dc.weather.sim_data]
            )

    def test_read_epw(self):
        # read back cached filled epw files
        for dc in self.data_clients:
            if not dc.weather.data.empty:
                data, meta, meta_lines = dc.weather.read_epw(
                    dc.weather.epw_path
                )
                assert not data.empty
                assert all(
                    data.columns
                    == dc.weather.epw_columns
                    + [EnergyPlusWeather.datetime_column]
                )

    def test_data_utc(self):

        for dc in self.data_clients:
            if not dc.hvac.data.empty:
                assert (
                    dc.hvac.data[dc.hvac.spec.datetime_column].dt.tz
                    == pytz.utc
                )
            if not dc.weather.data.empty:
                assert (
                    dc.weather.data[dc.weather.spec.datetime_column].dt.tz
                    == pytz.utc
                )

    def test_fill_missing_data(self):
        """Check that filled data exists and doesnt over fill"""
        for dc in self.data_clients:
            if (
                dc.sim_config["identifier"]
                == "2df6959cdf502c23f04f3155758d7b678af0c631"
            ):
                # verify that data ffill and bfill works with full_data_periods
                assert (
                    pytest.approx(21.11111)
                    == dc.hvac.data[1382:1385][STATES.TEMPERATURE_CTRL].mean()
                )
                assert (
                    pytest.approx(20.555555)
                    == dc.hvac.data[1385:1389][STATES.TEMPERATURE_CTRL].mean()
                )
                assert dc.full_data_periods[0] == (
                    pd.to_datetime("2018-04-13 17:00:00", utc=True),
                    pd.to_datetime("2018-04-26 16:10:00", utc=True),
                )
