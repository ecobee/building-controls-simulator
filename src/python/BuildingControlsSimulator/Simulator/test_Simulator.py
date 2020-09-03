# created by Tom Stesco tom.s@ecobee.com

import logging

import pytest
import pandas as pd
import os
import shutil

from BuildingControlsSimulator.Simulator.Simulation import Simulation
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

    @classmethod
    def teardown_class(cls):
        """ teardown any state that was previously setup with a call to
        setup_class.
        """
        pass

    @pytest.mark.skip()
    def test_deadband_fmu_simulation_equivalence(self):
        # test HVAC data returns dict of non-empty pd.DataFrame
        s = Simulation(
            building_model=EnergyPlusBuildingModel(
                idf=IDFPreprocessor(
                    idf_file=self.idf_name, init_temperature=22.0,
                ),
                weather_file=self.test_weather_path,
            ),
            controller_model=Deadband(
                deadband=2.0, stp_heat=21.0, stp_cool=24.0
            ),
            step_size_minutes=5,
            start_time_days=182,
            final_time_days=189,
        )

        s.create_models(preprocess_check=False)

        output_df_python = s.run()

        s = Simulation(
            building_model=EnergyPlusBuildingModel(
                idf=IDFPreprocessor(
                    idf_file=self.idf_name, init_temperature=22.0,
                ),
                weather_file=self.test_weather_path,
            ),
            controller_model=FMIController(
                fmu_path=self.deadband_fmu_path,
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
        assert output_df_python.equals(output_df_fmi)

    @pytest.mark.skip()
    def test_idmt_fmu_simulation(self):
        s = Simulation(
            building_model=EnergyPlusBuildingModel(
                idf=IDFPreprocessor(
                    idf_file=self.idf_name, init_temperature=22.0,
                ),
                weather_file=self.test_weather_path,
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
