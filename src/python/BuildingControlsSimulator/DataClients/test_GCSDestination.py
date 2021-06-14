# created by Tom Stesco tom.s@ecobee.com
import logging
import os
import copy

import pytest
import pandas as pd
import pytz

from BuildingControlsSimulator.Simulator.Config import Config
from BuildingControlsSimulator.DataClients.DataClient import DataClient
from BuildingControlsSimulator.DataClients.LocalSource import LocalSource
from BuildingControlsSimulator.DataClients.GCSDestination import GCSDestination
from BuildingControlsSimulator.DataClients.DataSpec import EnergyPlusWeather
from BuildingControlsSimulator.DataClients.DataStates import STATES
from BuildingControlsSimulator.DataClients.DataSpec import (
    Internal,
    DonateYourDataSpec,
    convert_spec,
)

logger = logging.getLogger(__name__)


@pytest.mark.skipif(
    (not os.environ.get("BCS_GOOGLE_CLOUD_PROJECT"))
    or (not os.environ.get("BCS_OUTPUT_GCS_URI_BASE")),
    reason="GCS output not configured.",
)
class TestGCSDestination:
    @classmethod
    def setup_class(cls):
        # initialize with data to avoid pulling multiple times
        cls.sim_config = Config.make_sim_config(
            identifier=[
                "DYD_dummy_data",
            ],  # test file
            latitude=33.481136,
            longitude=-112.078232,
            start_utc=[
                "2018-01-01 00:00:00",
            ],
            end_utc=[
                "2018-12-31 23:55:00",
            ],
            min_sim_period="3D",
            min_chunk_period="30D",
            sim_step_size_seconds=300,
            output_step_size_seconds=300,
        )

        cls.data_client = DataClient(
            source=LocalSource(
                local_cache=os.environ.get("LOCAL_CACHE_DIR"),
                data_spec=DonateYourDataSpec(),
            ),
            destination=GCSDestination(
                gcp_project=os.environ.get("BCS_GOOGLE_CLOUD_PROJECT"),
                gcs_uri_base=os.environ.get("BCS_OUTPUT_GCS_URI_BASE"),
                data_spec=DonateYourDataSpec(),
                local_cache=None,
            ),
            nrel_dev_api_key=os.environ.get("NREL_DEV_API_KEY"),
            nrel_dev_email=os.environ.get("NREL_DEV_EMAIL"),
            archive_tmy3_dir=os.environ.get("ARCHIVE_TMY3_DIR"),
            archive_tmy3_meta=os.environ.get("ARCHIVE_TMY3_META"),
            archive_tmy3_data_dir=os.environ.get("ARCHIVE_TMY3_DATA_DIR"),
            ep_tmy3_cache_dir=os.environ.get("EP_TMY3_CACHE_DIR"),
            simulation_epw_dir=os.environ.get("SIMULATION_EPW_DIR"),
        )
        cls.data_client.sim_config = cls.sim_config.iloc[0]

        cls.data_client.get_data()

    @classmethod
    def teardown_class(cls):
        """teardown any state that was previously setup with a call to
        setup_class.
        """
        pass

    def get_sim_name(self):
        _prefix = "sim"
        _sim_run_identifier = "test_run"
        _data_source = self.data_client.source.source_name
        _identifier = self.data_client.sim_config["identifier"]
        _building_model_name = "dummy_building"
        _controller_model_name = "dummy_controller"

        return "_".join(
            [
                _prefix,
                _sim_run_identifier,
                _data_source,
                _identifier,
                _building_model_name,
                _controller_model_name,
            ]
        )

    def test_put_data(self):
        sim_name = self.get_sim_name()
        _df = self.data_client.get_full_input()
        self.data_client.destination.put_data(_df, sim_name, src_spec=Internal())
        _gcs_uri = self.data_client.destination.get_gcs_uri(sim_name)

        r_df = pd.read_parquet(_gcs_uri)
        cr_df = convert_spec(
            r_df,
            src_spec=self.data_client.destination.data_spec,
            dest_spec=Internal(),
            src_nullable=True,
            dest_nullable=True,
        )

        # remove states not in dest spec
        for _col in _df.columns:
            _state = [
                v["internal_state"]
                for k, v in self.data_client.destination.data_spec.full.spec.items()
                if v["internal_state"] == _col
            ]
            if not _state:
                _df = _df.drop(columns=[_col])

        assert _df.equals(cr_df)
