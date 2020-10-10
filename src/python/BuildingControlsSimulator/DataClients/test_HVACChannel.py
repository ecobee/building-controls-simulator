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


class TestGCSDYDSource:
    @classmethod
    def setup_class(cls):
        # initialize with data to avoid pulling multiple times
        cls.sim_config = Config.make_sim_config(
            identifier=[
                "9958f46d13419344ec0c21fb60f9b0b3990ac0ef"
                # "bea5a8c53bd186378b40983b53f5f3d8ad76c97b",  # many custom schedules
            ],
            latitude=33.481136,
            longitude=-112.078232,
            start_utc=[
                "2018-01-01 00:00:00",
            ],
            end_utc=[
                "2018-12-31 23:55:00",
            ],
            min_sim_period="7D",
            min_chunk_period="30D",
            step_size_minutes=5,
        )

        cls.data_clients = []
        cls.data_client = DataClient(
            source=GCSDYDSource(
                gcp_project=os.environ.get("DYD_GOOGLE_CLOUD_PROJECT"),
                gcs_uri_base=os.environ.get("DYD_GCS_URI_BASE"),
            ),
            meta_gs_uri=os.environ.get("DYD_METADATA_URI"),
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
        """teardown any state that was previously setup with a call to
        setup_class.
        """
        pass

    def test_get_settings_change_points(self):
        # test HVAC data returns dict of non-empty pd.DataFrame
        for dc in self.data_clients:
            breakpoint()
            if (
                dc.sim_config["identifier"]
                == "2df6959cdf502c23f04f3155758d7b678af0c631"
            ):
                # verify that data bfill works with full_data_periods
                assert (
                    pytest.approx(30.0)
                    == dc.hvac.data[20620:20627][
                        STATES.TEMPERATURE_CTRL
                    ].mean()
                )
                assert dc.full_data_periods[0] == [
                    pd.Timestamp("2018-04-13 17:00:00", tz="utc"),
                    pd.Timestamp("2018-04-26 15:55:00", tz="utc"),
                ]

    def _return_change_points_schedule():
        return {
            Timestamp("2018-01-01 18:00:00+0000", tz="UTC"): [
                {
                    "name": "Home",
                    "minute_of_day": 1080,
                    "on_day_of_week": [
                        True,
                        False,
                        True,
                        True,
                        True,
                        True,
                        True,
                    ],
                },
                {
                    "name": "Sleep",
                    "minute_of_day": 1290,
                    "on_day_of_week": [
                        True,
                        False,
                        True,
                        True,
                        True,
                        True,
                        True,
                    ],
                },
                {
                    "name": "Away",
                    "minute_of_day": 510,
                    "on_day_of_week": [
                        True,
                        True,
                        True,
                        True,
                        True,
                        True,
                        True,
                    ],
                },
            ],
            Timestamp("2018-01-09 18:00:00+0000", tz="UTC"): [
                {
                    "name": "Home",
                    "minute_of_day": 1080,
                    "on_day_of_week": [
                        True,
                        True,
                        True,
                        True,
                        True,
                        True,
                        True,
                    ],
                },
                {
                    "name": "Sleep",
                    "minute_of_day": 1290,
                    "on_day_of_week": [
                        True,
                        True,
                        True,
                        True,
                        True,
                        True,
                        True,
                    ],
                },
                {
                    "name": "Away",
                    "minute_of_day": 510,
                    "on_day_of_week": [
                        True,
                        True,
                        True,
                        True,
                        True,
                        True,
                        True,
                    ],
                },
            ],
            Timestamp("2018-02-12 08:30:00+0000", tz="UTC"): [
                {
                    "name": "Home",
                    "minute_of_day": 1080,
                    "on_day_of_week": [
                        True,
                        True,
                        True,
                        True,
                        True,
                        True,
                        True,
                    ],
                },
                {
                    "name": "Sleep",
                    "minute_of_day": 1290,
                    "on_day_of_week": [
                        True,
                        True,
                        True,
                        True,
                        True,
                        True,
                        True,
                    ],
                },
                {
                    "name": "Away",
                    "minute_of_day": 510,
                    "on_day_of_week": [
                        False,
                        True,
                        True,
                        True,
                        True,
                        True,
                        True,
                    ],
                },
            ],
            Timestamp("2018-02-19 08:30:00+0000", tz="UTC"): [
                {
                    "name": "Away",
                    "minute_of_day": 510,
                    "on_day_of_week": [
                        True,
                        True,
                        True,
                        True,
                        True,
                        True,
                        True,
                    ],
                },
                {
                    "name": "Home",
                    "minute_of_day": 1080,
                    "on_day_of_week": [
                        True,
                        True,
                        True,
                        True,
                        True,
                        True,
                        True,
                    ],
                },
                {
                    "name": "Sleep",
                    "minute_of_day": 1290,
                    "on_day_of_week": [
                        True,
                        True,
                        True,
                        True,
                        True,
                        True,
                        True,
                    ],
                },
            ],
            Timestamp("2018-07-07 16:25:00+0000", tz="UTC"): [
                {
                    "name": "Home",
                    "minute_of_day": 985,
                    "on_day_of_week": [
                        False,
                        False,
                        False,
                        False,
                        False,
                        True,
                        False,
                    ],
                },
                {
                    "name": "Sleep",
                    "minute_of_day": 1290,
                    "on_day_of_week": [
                        False,
                        True,
                        True,
                        True,
                        True,
                        True,
                        True,
                    ],
                },
                {
                    "name": "Home",
                    "minute_of_day": 480,
                    "on_day_of_week": [
                        False,
                        False,
                        False,
                        False,
                        False,
                        True,
                        True,
                    ],
                },
                {
                    "name": "Away",
                    "minute_of_day": 510,
                    "on_day_of_week": [
                        True,
                        True,
                        True,
                        True,
                        False,
                        False,
                        False,
                    ],
                },
                {
                    "name": "Home",
                    "minute_of_day": 1080,
                    "on_day_of_week": [
                        True,
                        True,
                        True,
                        True,
                        True,
                        False,
                        False,
                    ],
                },
            ],
            Timestamp("2018-07-16 21:30:00+0000", tz="UTC"): [
                {
                    "name": "Sleep",
                    "minute_of_day": 1290,
                    "on_day_of_week": [
                        True,
                        True,
                        True,
                        True,
                        True,
                        True,
                        True,
                    ],
                },
                {
                    "name": "Away",
                    "minute_of_day": 510,
                    "on_day_of_week": [
                        True,
                        True,
                        True,
                        True,
                        True,
                        False,
                        False,
                    ],
                },
                {
                    "name": "Home",
                    "minute_of_day": 1080,
                    "on_day_of_week": [
                        True,
                        True,
                        True,
                        True,
                        True,
                        False,
                        False,
                    ],
                },
                {
                    "name": "Home",
                    "minute_of_day": 480,
                    "on_day_of_week": [
                        False,
                        False,
                        False,
                        False,
                        False,
                        True,
                        True,
                    ],
                },
            ],
        }
