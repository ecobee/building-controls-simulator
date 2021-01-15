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
from BuildingControlsSimulator.DataClients.DataSpec import DonateYourDataSpec
from BuildingControlsSimulator.DataClients.DataSpec import EnergyPlusWeather
from BuildingControlsSimulator.DataClients.DataStates import STATES
from BuildingControlsSimulator.DataClients.LocalDestination import (
    LocalDestination,
)

logger = logging.getLogger(__name__)


class TestGCSDYDSource:
    @classmethod
    def setup_class(cls):
        # initialize with data to avoid pulling multiple times
        cls.sim_config = Config.make_sim_config(
            identifier=[
                "d310f1c1f600c374d8975c753f7c0fb8de9c96b1",
                "8c00c9bb17bfcca53809cb1b2d033a448bc017df",  # has full data periods
                "6773291da5427ae87d34bb75022ee54ee3b1fc17",  # file not found
            ],
            latitude=33.481136,
            longitude=-112.078232,
            start_utc=[
                "2018-01-01 00:00:00",
                "2018-01-01 00:00:00",
                "2018-01-01 00:00:00",
            ],
            end_utc=[
                "2018-12-31 23:55:00",
                "2018-12-31 23:55:00",
                "2018-12-31 23:55:00",
            ],
            min_sim_period="7D",
            min_chunk_period="30D",
            sim_step_size_seconds=300,
            output_step_size_seconds=300,
        )

        cls.data_clients = []

        # set local_cache=None to test connection with GCS
        cls.data_client = DataClient(
            source=GCSDYDSource(
                gcp_project=os.environ.get("DYD_GOOGLE_CLOUD_PROJECT"),
                gcs_uri_base=os.environ.get("DYD_GCS_URI_BASE"),
                local_cache=None,
            ),
            destination=LocalDestination(
                local_cache=os.environ.get("LOCAL_CACHE_DIR"),
                data_spec=DonateYourDataSpec(),
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

            if _sim_config["identifier"] in [
                "6773291da5427ae87d34bb75022ee54ee3b1fc17",
            ]:
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
                    sim_config=dc.sim_config, datetime_channel=dc.datetime
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
            if (
                dc.sim_config["identifier"]
                == "8c00c9bb17bfcca53809cb1b2d033a448bc017df"
            ):
                # verify that data bfill works with full_data_periods
                assert (
                    pytest.approx(21.037790298461914)
                    == dc.thermostat.data.iloc[
                        dc.datetime.data[
                            (
                                dc.datetime.data[STATES.DATE_TIME]
                                >= pd.Timestamp("2018-02-21 16:25:00+0000", tz="UTC")
                            )
                            & (
                                dc.datetime.data[STATES.DATE_TIME]
                                <= pd.Timestamp("2018-02-26 17:00:00+0000", tz="UTC")
                            )
                        ].index,
                    ][STATES.TEMPERATURE_CTRL].mean()
                )
                assert dc.full_data_periods[0] == [
                    pd.Timestamp("2018-02-10 17:00:00+0000", tz="UTC"),
                    pd.Timestamp("2018-02-21 16:25:00+0000", tz="UTC"),
                ]
