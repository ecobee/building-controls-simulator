# created by Tom Stesco tom.s@ecobee.com
import logging
import os
import copy

import pytest
import pandas as pd
import numpy as np
import pytz

from BuildingControlsSimulator.Simulator.Config import Config
from BuildingControlsSimulator.DataClients.DataClient import DataClient
from BuildingControlsSimulator.DataClients.GCSDYDSource import GCSDYDSource
from BuildingControlsSimulator.DataClients.DataSpec import DonateYourDataSpec
from BuildingControlsSimulator.DataClients.DataSpec import EnergyPlusWeather
from BuildingControlsSimulator.DataClients.DataStates import STATES
from BuildingControlsSimulator.DataClients.LocalDestination import LocalDestination

logger = logging.getLogger(__name__)

@pytest.mark.skipif(
    (not os.environ.get("DYD_GOOGLE_CLOUD_PROJECT"))
    or (not os.environ.get("DYD_GCS_URI_BASE")),
    reason="GCS output not configured.",
)
class TestGCSDYDSource:
    @classmethod
    def setup_class(cls):
        # initialize with data to avoid pulling multiple times
        cls.sim_config = Config.make_sim_config(
            identifier=["9958f46d13419344ec0c21fb60f9b0b3990ac0ef"],
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
            sim_step_size_seconds=300,
            output_step_size_seconds=300,
        )

        cls.data_clients = []
        cls.data_client = DataClient(
            source=GCSDYDSource(
                gcp_project=os.environ.get("DYD_GOOGLE_CLOUD_PROJECT"),
                gcs_uri_base=os.environ.get("DYD_GCS_URI_BASE"),
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
            if (
                dc.sim_config["identifier"]
                == "9958f46d13419344ec0c21fb60f9b0b3990ac0ef"
            ):
                assert (
                    dc.thermostat.change_points_schedule
                    == TestGCSDYDSource._return_change_points_schedule()
                )
                assert (
                    dc.thermostat.change_points_comfort_prefs
                    == TestGCSDYDSource._return_change_points_comfort_prefs()
                )
                assert dc.thermostat.change_points_hvac_mode == {
                    pd.Timestamp("2018-01-01 17:00:00+0000", tz="UTC"): "auto"
                }

    @staticmethod
    def _return_change_points_schedule():
        return {
            pd.Timestamp("2018-01-01 18:00:00+0000", tz="UTC"): [
                {
                    "minute_of_day": 1080,
                    "name": "Home",
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
                    "minute_of_day": 1290,
                    "name": "Sleep",
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
                    "minute_of_day": 510,
                    "name": "Away",
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
            pd.Timestamp("2018-07-07 16:25:00+0000", tz="UTC"): [
                {
                    "minute_of_day": 985,
                    "name": "Home",
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
                    "minute_of_day": 1290,
                    "name": "Sleep",
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
                    "minute_of_day": 480,
                    "name": "Home",
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
                    "minute_of_day": 510,
                    "name": "Away",
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
                    "minute_of_day": 1080,
                    "name": "Home",
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
            pd.Timestamp("2018-07-14 16:25:00+0000", tz="UTC"): [
                {
                    "minute_of_day": 1290,
                    "name": "Sleep",
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
                    "minute_of_day": 480,
                    "name": "Home",
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
                    "minute_of_day": 510,
                    "name": "Away",
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
                    "minute_of_day": 1080,
                    "name": "Home",
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
        }

    @staticmethod
    def _return_change_points_comfort_prefs():
        return {
            pd.Timestamp("2018-01-01 17:05:00+0000", tz="UTC"): {
                "Away": {
                    STATES.TEMPERATURE_STP_COOL: np.float32(27.777779),
                    STATES.TEMPERATURE_STP_HEAT: np.float32(17.777779),
                }
            },
            pd.Timestamp("2018-01-01 18:05:00+0000", tz="UTC"): {
                "Home": {
                    STATES.TEMPERATURE_STP_COOL: np.float32(25.555555),
                    STATES.TEMPERATURE_STP_HEAT: np.float32(18.88889),
                }
            },
            pd.Timestamp("2018-03-23 19:55:00+0000", tz="UTC"): {
                "Home": {
                    STATES.TEMPERATURE_STP_COOL: np.float32(26.66666603088379),
                    STATES.TEMPERATURE_STP_HEAT: np.float32(18.33333396911621),
                }
            },
            pd.Timestamp("2018-03-23 20:00:00+0000", tz="UTC"): {
                "Home": {
                    STATES.TEMPERATURE_STP_COOL: np.float32(25.55555534362793),
                    STATES.TEMPERATURE_STP_HEAT: np.float32(18.88888931274414),
                }
            },
            pd.Timestamp("2018-04-06 18:05:00+0000", tz="UTC"): {
                "Home": {
                    STATES.TEMPERATURE_STP_COOL: np.float32(26.11111068725586),
                    STATES.TEMPERATURE_STP_HEAT: np.float32(18.88888931274414),
                }
            },
            pd.Timestamp("2018-04-14 19:55:00+0000", tz="UTC"): {
                "Home": {
                    STATES.TEMPERATURE_STP_COOL: np.float32(26.11111068725586),
                    STATES.TEMPERATURE_STP_HEAT: np.float32(18.33333396911621),
                }
            },
            pd.Timestamp("2018-04-14 20:00:00+0000", tz="UTC"): {
                "Home": {
                    STATES.TEMPERATURE_STP_COOL: np.float32(26.11111068725586),
                    STATES.TEMPERATURE_STP_HEAT: np.float32(18.88888931274414),
                }
            },
            pd.Timestamp("2018-04-17 19:10:00+0000", tz="UTC"): {
                "Home": {
                    STATES.TEMPERATURE_STP_COOL: np.float32(26.66666603088379),
                    STATES.TEMPERATURE_STP_HEAT: np.float32(18.88888931274414),
                }
            },
            pd.Timestamp("2018-07-08 09:45:00+0000", tz="UTC"): {
                "Home": {
                    STATES.TEMPERATURE_STP_COOL: np.float32(26.11111068725586),
                    STATES.TEMPERATURE_STP_HEAT: np.float32(18.88888931274414),
                }
            },
            pd.Timestamp("2018-07-08 09:50:00+0000", tz="UTC"): {
                "Home": {
                    STATES.TEMPERATURE_STP_COOL: np.float32(25.55555534362793),
                    STATES.TEMPERATURE_STP_HEAT: np.float32(18.88888931274414),
                }
            },
            pd.Timestamp("2018-07-24 19:55:00+0000", tz="UTC"): {
                "Home": {
                    STATES.TEMPERATURE_STP_COOL: np.float32(25.55555534362793),
                    STATES.TEMPERATURE_STP_HEAT: np.float32(18.33333396911621),
                }
            },
            pd.Timestamp("2018-07-24 20:00:00+0000", tz="UTC"): {
                "Home": {
                    STATES.TEMPERATURE_STP_COOL: np.float32(25.55555534362793),
                    STATES.TEMPERATURE_STP_HEAT: np.float32(18.88888931274414),
                }
            },
            pd.Timestamp("2018-09-09 11:25:00+0000", tz="UTC"): {
                "Home": {
                    STATES.TEMPERATURE_STP_COOL: np.float32(26.66666603088379),
                    STATES.TEMPERATURE_STP_HEAT: np.float32(18.33333396911621),
                }
            },
            pd.Timestamp("2018-09-09 11:30:00+0000", tz="UTC"): {
                "Home": {
                    STATES.TEMPERATURE_STP_COOL: np.float32(25.55555534362793),
                    STATES.TEMPERATURE_STP_HEAT: np.float32(18.88888931274414),
                }
            },
            pd.Timestamp("2018-01-01 21:35:00+0000", tz="UTC"): {
                "Sleep": {
                    STATES.TEMPERATURE_STP_COOL: np.float32(25.555555),
                    STATES.TEMPERATURE_STP_HEAT: np.float32(18.88889),
                }
            },
            pd.Timestamp("2018-03-31 21:35:00+0000", tz="UTC"): {
                "Sleep": {
                    STATES.TEMPERATURE_STP_COOL: np.float32(24.44444465637207),
                    STATES.TEMPERATURE_STP_HEAT: np.float32(18.88888931274414),
                }
            },
        }
