# created by Tom Stesco tom.s@ecobee.com

import logging

import pytest
import pandas as pd
import os

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
        pass

    @classmethod
    def teardown_class(cls):
        """ teardown any state that was previously setup with a call to
        setup_class.
        """
        pass

    def test_deadband_fmu_simulation_equivalence(self):
        # test HVAC data returns dict of non-empty pd.DataFrame
        s = Simulation(
            building_model=EnergyPlusBuildingModel(
                idf=IDFPreprocessor(
                    idf_file="AZ_Phoenix_gasfurnace_crawlspace_IECC_2018_cycles.idf",
                    init_temperature=22.0,
                ),
                weather_file="USA_AZ_Phoenix-Sky.Harbor.Intl.AP.722780_TMY3.epw",
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
                    idf_file="AZ_Phoenix_gasfurnace_crawlspace_IECC_2018_cycles.idf",
                    init_temperature=22.0,
                ),
                weather_file="USA_AZ_Phoenix-Sky.Harbor.Intl.AP.722780_TMY3.epw",
            ),
            controller_model=FMIController(
                fmu_path=f"{os.environ.get('FMU_DIR')}/../fmu-models/deadband/deadband.fmu",
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
