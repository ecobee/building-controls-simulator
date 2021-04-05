# created by Tom Stesco tom.s@ecobee.com

import logging
import copy

import pytest
import pandas as pd
import pytz
import os

from BuildingControlsSimulator.Simulator.Config import Config
from BuildingControlsSimulator.DataClients.DataClient import DataClient
from BuildingControlsSimulator.DataClients.GBQDataSource import (
    GBQDataSource,
)
from BuildingControlsSimulator.DataClients.DataSpec import FlatFilesSpec
from BuildingControlsSimulator.DataClients.LocalDestination import (
    LocalDestination,
)
from BuildingControlsSimulator.DataClients.DataSpec import EnergyPlusWeather
from BuildingControlsSimulator.DataClients.DataStates import STATES

logger = logging.getLogger(__name__)


class TestGBQFlatFilesSource:
    @classmethod
    def setup_class(cls):
        # initialize with data to avoid pulling multiple times
        cls.sim_config = Config.make_sim_config(
            identifier=[
                os.environ.get("TEST_FLATFILES_GBQ_IDENTIFIER"),  # has all holds
                "9999999",  # file not found
            ],
            latitude=33.481136,
            longitude=-112.078232,
            start_utc="2019-01-02 00:00:00",
            end_utc="2019-02-01 00:00:00",
            min_sim_period="3D",
            sim_step_size_seconds=300,
            output_step_size_seconds=300,
        )

        cls.data_clients = []

        # set local_cache=None to test connection with GCS
        cls.data_client = DataClient(
            source=GBQDataSource(
                gcp_project=os.environ.get("FLATFILE_GOOGLE_CLOUD_PROJECT"),
                gbq_table=os.environ.get("FLATFILES_GBQ_TABLE"),
                data_spec=FlatFilesSpec(),
                local_cache=None,
            ),
            destination=LocalDestination(
                local_cache=os.environ.get("LOCAL_CACHE_DIR"),
                data_spec=FlatFilesSpec(),
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
            if _sim_config["identifier"] == "9999999":
                with pytest.raises(ValueError):
                    dc.get_data()
            else:
                dc.get_data()

            cls.data_clients.append(dc)

    @classmethod
    def teardown_class(cls):
        """teardown any state that was previously setup with a call to
        setup_class.
        """
        pass

    def test_get_data(self):
        # test HVAC data returns dict of non-empty pd.DataFrame
        for dc in self.data_clients:
            if dc.datetime:
                assert isinstance(dc.datetime.data, pd.DataFrame)
                assert isinstance(dc.thermostat.data, pd.DataFrame)
                assert isinstance(dc.equipment.data, pd.DataFrame)
                assert isinstance(dc.sensors.data, pd.DataFrame)
                assert isinstance(dc.weather.data, pd.DataFrame)

    def test_read_epw(self):
        # read back cached filled epw files
        for dc in self.data_clients:
            if dc.weather and not dc.weather.data.empty:
                # generate the epw file before checking it
                _epw_path = dc.weather.make_epw_file(
                    sim_config=dc.sim_config,
                    datetime_channel=dc.datetime,
                    epw_step_size_seconds=dc.sim_config["sim_step_size_seconds"],
                )
                data, meta, meta_lines = dc.weather.read_epw(_epw_path)
                assert not data.empty
                assert all(data.columns == dc.weather.epw_columns)

    def test_data_utc(self):
        for dc in self.data_clients:
            if dc.datetime and not dc.datetime.data.empty:
                assert (
                    dc.datetime.data[dc.datetime.spec.datetime_column].dtype.tz
                    == pytz.utc
                )

    def test_fill_missing_data(self):
        """Check that filled data exists and doesnt over fill"""
        for dc in self.data_clients:
            if dc.sim_config["identifier"] == os.environ.get(
                "TEST_FLATFILES_GBQ_IDENTIFIER"
            ):
                # verify that data bfill works with full_data_periods
                assert (
                    pytest.approx(24.69999885559082)
                    == dc.thermostat.data.iloc[
                        dc.datetime.data[
                            (
                                dc.datetime.data[STATES.DATE_TIME]
                                >= pd.Timestamp("2019-01-07 11:20", tz="utc")
                            )
                            & (
                                dc.datetime.data[STATES.DATE_TIME]
                                <= pd.Timestamp("2019-01-07 11:40:00", tz="utc")
                            )
                        ].index,
                    ][STATES.TEMPERATURE_CTRL].mean()
                )
                assert dc.full_data_periods[0] == [
                    pd.to_datetime("2019-01-02 00:00:00", utc=True),
                    pd.to_datetime("2019-01-07 11:20:00", utc=True),
                ]
