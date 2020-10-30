# created by Tom Stesco tom.s@ecobee.com

import logging

import pytest
import pandas as pd
import os
import shutil

from BuildingControlsSimulator.Simulator.Simulator import Simulator
from BuildingControlsSimulator.Simulator.Config import Config
from BuildingControlsSimulator.DataClients.DataClient import DataClient
from BuildingControlsSimulator.DataClients.GCSDYDSource import GCSDYDSource
from BuildingControlsSimulator.BuildingModels.IDFPreprocessor import (
    IDFPreprocessor,
)
from BuildingControlsSimulator.BuildingModels.EnergyPlusBuildingModel import (
    EnergyPlusBuildingModel,
)
from BuildingControlsSimulator.DataClients.LocalDestination import (
    LocalDestination,
)
from BuildingControlsSimulator.DataClients.DataSpec import (
    DonateYourDataSpec,
    Internal,
)
from BuildingControlsSimulator.ControllerModels.FMIController import (
    FMIController,
)
from BuildingControlsSimulator.ControllerModels.Deadband import Deadband
from BuildingControlsSimulator.DataClients.DataStates import STATES
from BuildingControlsSimulator.StateEstimatorModels.LowPassFilter import (
    LowPassFilter,
)

logger = logging.getLogger(__name__)


class TestSimulator:
    @classmethod
    def setup_class(cls):
        # initialize with data to avoid pulling multiple times

        EnergyPlusBuildingModel.make_directories()

        # the weather file here does not need to be correct for IDF file
        # this is closest file found in standard EPlus installation
        weather_name = "USA_FL_Tampa.Intl.AP.722110_TMY3.epw"
        cls.test_weather_path = os.path.join(
            os.environ.get("WEATHER_DIR"), weather_name
        )
        if not os.path.isfile(cls.test_weather_path):
            _fpath = os.path.join(
                os.environ.get("EPLUS_DIR"),
                "WeatherData",
                weather_name,
            )
            shutil.copyfile(_fpath, cls.test_weather_path)

        cls.idf_name = "AZ_Phoenix_gasfurnace_crawlspace_IECC_2018_cycles.idf"

        cls.deadband_fmu_path = (
            f"{os.environ.get('FMU_DIR')}/../fmu-models/deadband/deadband.fmu"
        )

        cls.dc = DataClient(
            source=GCSDYDSource(
                gcp_project=os.environ.get("GOOGLE_CLOUD_PROJECT"),
                gcs_uri_base=os.environ.get("DYD_GCS_URI_BASE"),
                local_cache=os.environ.get("LOCAL_CACHE_DIR"),
            ),
            destination=LocalDestination(
                local_cache=os.environ.get("LOCAL_CACHE_DIR"),
                data_spec=Internal(),
            ),
            nrel_dev_api_key=os.environ.get("NREL_DEV_API_KEY"),
            nrel_dev_email=os.environ.get("NREL_DEV_EMAIL"),
            archive_tmy3_meta=os.environ.get("ARCHIVE_TMY3_META"),
            archive_tmy3_data_dir=os.environ.get("ARCHIVE_TMY3_DATA_DIR"),
            ep_tmy3_cache_dir=os.environ.get("EP_TMY3_CACHE_DIR"),
            simulation_epw_dir=os.environ.get("SIMULATION_EPW_DIR"),
        )

    @classmethod
    def teardown_class(cls):
        """teardown any state that was previously setup with a call to
        setup_class.
        """
        pass

    def test_deadband_ts_300(self):
        test_sim_config = Config.make_sim_config(
            identifier=[
                "2df6959cdf502c23f04f3155758d7b678af0c631",  # has full data periods
            ],
            latitude=33.481136,
            longitude=-112.078232,
            start_utc="2018-05-16",
            end_utc="2018-06-01",
            min_sim_period="3D",
            min_chunk_period="30D",
            sim_step_size_seconds=300,
            output_step_size_seconds=300,
        )

        # test HVAC data returns dict of non-empty pd.DataFrame
        master = Simulator(
            data_client=self.dc,
            sim_config=test_sim_config,
            building_models=[
                EnergyPlusBuildingModel(
                    idf=IDFPreprocessor(
                        idf_file=self.idf_name,
                    ),
                )
            ],
            controller_models=[
                Deadband(deadband=1.0),
            ],
            state_estimator_models=[
                LowPassFilter(alpha_temperature=0.3, alpha_humidity=0.3)
            ],
        )
        master.simulate(local=True, preprocess_check=False)

        assert (
            pytest.approx(26.66449546813965)
            == master.simulations[0]
            .output[STATES.THERMOSTAT_TEMPERATURE]
            .mean()
        )
        assert (
            pytest.approx(18.17778778076172)
            == master.simulations[0].output[STATES.THERMOSTAT_HUMIDITY].mean()
        )

        # read back stored output and check it
        sim_name = master.simulations[0].sim_name
        _fpath = os.path.join(
            master.simulations[0].data_client.destination.local_cache,
            master.simulations[0].data_client.destination.operator_name,
            sim_name
            + "."
            + master.simulations[0].data_client.destination.file_extension,
        )
        r_df = pd.read_parquet(_fpath)

        assert (
            pytest.approx(26.66449546813965)
            == r_df["thermostat_temperature"].mean()
        )
        assert (
            pytest.approx(18.17778778076172)
            == r_df["thermostat_humidity"].mean()
        )

    def test_deadband_ts_60(self):
        test_sim_config = Config.make_sim_config(
            identifier=[
                "2df6959cdf502c23f04f3155758d7b678af0c631",  # has full data periods
            ],
            latitude=33.481136,
            longitude=-112.078232,
            start_utc="2018-05-16",
            end_utc="2018-05-19",
            min_sim_period="1D",
            min_chunk_period="30D",
            sim_step_size_seconds=60,
            output_step_size_seconds=300,
        )

        # test HVAC data returns dict of non-empty pd.DataFrame
        master = Simulator(
            data_client=self.dc,
            sim_config=test_sim_config,
            building_models=[
                EnergyPlusBuildingModel(
                    idf=IDFPreprocessor(
                        idf_file=self.idf_name,
                    ),
                )
            ],
            controller_models=[
                Deadband(deadband=1.0),
            ],
            state_estimator_models=[
                LowPassFilter(alpha_temperature=0.3, alpha_humidity=0.3)
            ],
        )
        master.simulate(local=True, preprocess_check=False)
        assert (
            pytest.approx(27.066694259643555)
            == master.simulations[0]
            .output[STATES.THERMOSTAT_TEMPERATURE]
            .mean()
        )
        assert (
            pytest.approx(16.301517486572266)
            == master.simulations[0].output[STATES.THERMOSTAT_HUMIDITY].mean()
        )

        # read back stored output and check it
        sim_name = master.simulations[0].sim_name
        _fpath = os.path.join(
            master.simulations[0].data_client.destination.local_cache,
            master.simulations[0].data_client.destination.operator_name,
            sim_name
            + "."
            + master.simulations[0].data_client.destination.file_extension,
        )
        r_df = pd.read_parquet(_fpath)

        assert (
            pytest.approx(27.066694259643555)
            == r_df["thermostat_temperature"].mean()
        )
        assert (
            pytest.approx(16.301517486572266)
            == r_df["thermostat_humidity"].mean()
        )
