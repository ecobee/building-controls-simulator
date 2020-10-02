# created by Tom Stesco tom.s@ecobee.com

import logging
import copy

import pytest
import pandas as pd
import pytz
import os

from BuildingControlsSimulator.Simulator.Config import Config
from BuildingControlsSimulator.DataClients.DataClient import DataClient
from BuildingControlsSimulator.DataClients.GCSFlatFilesSource import (
    GCSFlatFilesSource,
)
from BuildingControlsSimulator.DataClients.DataSpec import EnergyPlusWeather
from BuildingControlsSimulator.DataClients.DataStates import STATES

logger = logging.getLogger(__name__)


class TestFlatFilesClient:
    @classmethod
    def setup_class(cls):
        # initialize with data to avoid pulling multiple times
        cls.sim_config = Config.make_sim_config(
            identifier=[
                os.environ.get("TEST_FLATFILES_IDENTIFIER_MISSING"),  # missing
                os.environ.get("TEST_FLATFILES_IDENTIFIER_FULL"),  # full
                "9999999",  # file not found
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
            source=GCSFlatFilesSource(
                gcp_project=os.environ.get("GOOGLE_CLOUD_PROJECT"),
                gcs_uri_base=os.environ.get("ISM_GCS_URI_BASE"),
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

    def test_get_data(self):
        # test HVAC data returns dict of non-empty pd.DataFrame
        for dc in self.data_clients:
            assert isinstance(dc.hvac.data, pd.DataFrame)
            assert isinstance(dc.sensors.data, pd.DataFrame)
            assert isinstance(dc.weather.data, pd.DataFrame)

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
            if dc.sim_config["identifier"] == os.environ.get(
                "TEST_FLATFILES_IDENTIFIER_FULL"
            ):
                # verify that data bfill works with full_data_periods
                assert (
                    pytest.approx(26.864197)
                    == dc.hvac.data[
                        (
                            dc.hvac.data[STATES.DATE_TIME]
                            >= pd.Timestamp("2018-06-18 22:10:00", tz="utc")
                        )
                        & (
                            dc.hvac.data[STATES.DATE_TIME]
                            <= pd.Timestamp("2018-06-18 22:50:00", tz="utc")
                        )
                    ][STATES.TEMPERATURE_CTRL].mean()
                )
                assert dc.full_data_periods[0] == [
                    pd.to_datetime("2018-06-10 04:00:00", utc=True),
                    pd.to_datetime("2018-06-18 22:10:00", utc=True),
                ]
