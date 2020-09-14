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

from BuildingControlsSimulator.ControlModels.FMIController import FMIController
from BuildingControlsSimulator.ControlModels.Deadband import Deadband

logger = logging.getLogger(__name__)


class TestSimulator:
    @classmethod
    def setup_class(cls):
        # initialize with data to avoid pulling multiple times

        EnergyPlusBuildingModel.make_directories()

        weather_name = "USA_FL_Tampa.Intl.AP.722110_TMY3.epw"
        cls.test_weather_path = os.path.join(
            os.environ.get("WEATHER_DIR"), weather_name
        )
        if not os.path.isfile(cls.test_weather_path):
            _fpath = os.path.join(
                os.environ.get("EPLUS_DIR"), "WeatherData", weather_name,
            )
            shutil.copyfile(_fpath, cls.test_weather_path)

        cls.idf_name = "AZ_Phoenix_gasfurnace_crawlspace_IECC_2018_cycles.idf"

        cls.deadband_fmu_path = (
            f"{os.environ.get('FMU_DIR')}/../fmu-models/deadband/deadband.fmu"
        )

        cls.idtm_fmu_path = f"{os.environ.get('FMU_DIR')}/../fmu-models/idtm.0f94bb5d90d898380ff165b5caf1a70171c3bacc.fmu"

        cls.dc = DataClient(
            source=GCSDYDSource(
                gcp_project=os.environ.get("GOOGLE_CLOUD_PROJECT"),
                gcs_uri_base=os.environ.get("DYD_GCS_URI_BASE"),
            ),
            nrel_dev_api_key=os.environ.get("NREL_DEV_API_KEY"),
            nrel_dev_email=os.environ.get("NREL_DEV_EMAIL"),
            archive_tmy3_meta=os.environ.get("ARCHIVE_TMY3_META"),
            archive_tmy3_data_dir=os.environ.get("ARCHIVE_TMY3_DATA_DIR"),
            ep_tmy3_cache_dir=os.environ.get("EP_TMY3_CACHE_DIR"),
            simulation_epw_dir=os.environ.get("SIMULATION_EPW_DIR"),
        )

        cls.sim_config = Config.make_sim_config(
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
            step_size_minutes=5,
        )

    @classmethod
    def teardown_class(cls):
        """ teardown any state that was previously setup with a call to
        setup_class.
        """
        pass

    # @pytest.mark.skip()
    def test_deadband_fmu_simulation_equivalence(self):
        # test HVAC data returns dict of non-empty pd.DataFrame
        master = Simulator(
            data_client=self.dc,
            sim_config=self.sim_config,
            building_models=[
                EnergyPlusBuildingModel(
                    idf=IDFPreprocessor(
                        idf_file=self.idf_name, init_temperature=22.0,
                    ),
                )
            ],
            controller_models=[Deadband(deadband=2.0),],
        )
        breakpoint()
        master.create_models(preprocess_check=False)

    @pytest.mark.skip()
    def test_idmt_fmu_simulation(self):
        s = Simulator(
            building_model=EnergyPlusBuildingModel(
                idf=IDFPreprocessor(
                    idf_file=self.idf_name, init_temperature=22.0,
                ),
                # weather_file=self.test_weather_path,
            ),
            controller_model=FMIController(
                fmu_path=self.idtm_fmu_path,
                deadband=2.0,
                stp_heat=21.0,
                stp_cool=24.0,
            ),
            step_size_minutes=5,
            start_time_days=182,
            final_time_days=189,
        )

        # don't need to recreate EnergyPlus FMU
        s.create_models(preprocess_check=True)

        output_df_fmi = s.run()
        print("ok")
