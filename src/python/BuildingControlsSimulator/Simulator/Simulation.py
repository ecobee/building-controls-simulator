# created by Tom Stesco tom.s@ecobee.com

import os
import logging

import pandas as pd
import numpy as np
import attr

from BuildingControlsSimulator.BuildingModels.EnergyPlusBuildingModel import (
    EnergyPlusBuildingModel,
)
from BuildingControlsSimulator.BuildingModels.IDFPreprocessor import (
    IDFPreprocessor,
)
from BuildingControlsSimulator.ControlModels.Deadband import Deadband
from BuildingControlsSimulator.OutputAnalysis.OutputAnalysis import (
    OutputAnalysis,
)

logger = logging.getLogger(__name__)


@attr.s(kw_only=True)
class Simulation:
    """Converts IDFs (Input Data Files) for EnergyPlus into working IDFs.
    """

    building_model = attr.ib()
    controller_model = attr.ib()
    # TODO add validator
    step_size_minutes = attr.ib()
    start_time_days = attr.ib()
    final_time_days = attr.ib()
    output_data_dir = attr.ib(
        default=os.path.join(os.environ.get("OUTPUT_DIR"), "data")
    )
    output_plot_dir = attr.ib(
        default=os.path.join(os.environ.get("OUTPUT_DIR"), "plot")
    )

    @property
    def steps_per_hour(self):
        return int(60 / self.step_size_minutes)

    @property
    def step_size_seconds(self):
        return int(self.step_size_minutes * 60)

    @property
    def start_time_seconds(self):
        return int(self.start_time_days * 86400)

    @property
    def final_time_seconds(self):
        return int(self.final_time_days * 86400)

    @property
    def simulator_output_keys(self):
        return ["time_seconds", "step_status", "t_ctrl"]

    @property
    def output_keys(self):
        return (
            self.simulator_output_keys
            + self.controller_model.output_keys()
            + list(self.building_model.fmu.get_model_variables().keys())
        )

    @property
    def building_model_output_keys(self):
        return self.building_model.fmu.get_model_variables().keys()

    def create_models(self, preprocess_check=False):
        self.building_model.idf.preprocess(
            timesteps_per_hour=self.steps_per_hour,
            preprocess_check=preprocess_check,
        )
        return self.building_model.create_model_fmu()

    def initialize(self):
        """initialize FMU models
        """
        self.building_model.initialize(
            self.start_time_seconds, self.final_time_seconds
        )
        self.controller_model.initialize(
            self.start_time_seconds, self.final_time_seconds
        )

    def get_air_temp_output_idx(self):
        """
        """
        air_temp_var_names = [
            "FMU_" + z + "_Zone_Air_Temperature"
            for z in self.building_model.occupied_zones()
        ]
        return [
            i
            for i, k in enumerate(
                self.building_model.fmu.get_model_variables().keys()
            )
            if k in air_temp_var_names
        ]

    def calc_T_control(self, building_model_output, air_temp_output_idx):
        """
        """
        return np.mean(building_model_output[air_temp_output_idx])

    def run(self):
        """
        """
        logger.info("Initializing FMU models ...")
        self.initialize()

        logger.info("Running co-simulation ...")
        output = []
        t_ctrl = self.building_model.init_temperature
        air_temp_output_idx = self.get_air_temp_output_idx()

        for t_step_seconds in range(
            self.start_time_seconds,
            self.final_time_seconds,
            self.step_size_seconds,
        ):
            # TODO: generalize controller_model.do_step to translate between
            # controller model inputs and outputs, i.e. use input time series
            # occupancy, setpoint changes, hvac mode changes
            controller_output = self.controller_model.do_step(t_ctrl)

            self.building_model.actuate_HVAC_equipment(
                self.controller_model.HVAC_mode
            )
            step_status = self.building_model.fmu.do_step(
                current_t=t_step_seconds,
                step_size=self.step_size_seconds,
                new_step=True,
            )
            # save data as row
            building_model_output = np.array(
                [
                    self.building_model.fmu.get(k)[0]
                    for k in self.building_model_output_keys
                ]
            )

            t_ctrl = self.calc_T_control(
                building_model_output, air_temp_output_idx
            )

            step_output = (
                [t_step_seconds, step_status, t_ctrl]
                + controller_output
                + list(building_model_output)
            )
            output.append(step_output)
            # TODO add multizone support

        self.output_df = pd.DataFrame.from_records(
            output, columns=self.output_keys
        )
        return self.output_df

    def show_plots(self):
        output_analysis = OutputAnalysis(df=self.output_df)
        output_analysis.postprocess()
        output_analysis.diagnostic_plot(show=True)
        # output_analysis.thermal_plot(show=True)
        # output_analysis.power_plot(show=True)
        # output_analysis.control_actuation_plot(show=True)
