#!/usr/bin/env python
# created by Tom Stesco tom.s@ecobee.com

import os
import subprocess

import pandas as pd
import numpy as np
import attr

import pyfmi

from BuildingControlSimulator.BuildingModels.EnergyPlusBuildingModel import EnergyPlusBuildingModel
from BuildingControlSimulator.BuildingModels.IDFPreprocessor import IDFPreprocessor
from BuildingControlSimulator.ControlModels.Deadband import Deadband

@attr.s
class Simulation(object):
    """Converts IDFs (Input Data Files) for EnergyPlus into working IDFs.

    Example:
    ```python


    ```

    """
    building_model = attr.ib(kw_only=True)
    controller = attr.ib(kw_only=True)
    # TODO add validator
    step_size_minutes = attr.ib(kw_only=True)
    start_time_days = attr.ib(kw_only=True)
    final_time_days = attr.ib(kw_only=True)
    output_data_dir = attr.ib(default=os.path.join(os.environ["PACKAGE_DIR"], "output/data"))
    output_plot_dir = attr.ib(default=os.path.join(os.environ["PACKAGE_DIR"], "output/plot"))
    # t_step_seconds = attr.ib(default=0)

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
        return self.simulator_output_keys + self.controller.output_keys() + list(self.building_model.fmu.get_model_variables().keys())

    @property
    def building_model_output_keys(self):
        return self.building_model.fmu.get_model_variables().keys()

    def initialize(self):
        self.building_model.idf.preprocess(timesteps_per_hour=self.steps_per_hour)
        self.building_model.initialize(self.start_time_seconds, self.final_time_seconds)
    
    def do_step(self):
        pass

    def get_air_temp_vars(self, step_output):
        return [step_output[i] for i, k 
            in enumerate(self.building_model_output_keys) 
            if "Zone_Air_Temperature" in k
        ]

    def calc_T_control(self, building_model_output):        
        return np.mean(self.get_air_temp_vars(building_model_output))
         

    def run(self):
        """
        """

        print("_"*80)
        print("Entering co-simulation loop")
        print("_"*80)
        output = []
        t_ctrl = self.building_model.init_temperature

        for t_step_seconds in range(self.start_time_seconds, self.final_time_seconds, self.step_size_seconds):
        # while self.t_step_seconds <= self.final_time_seconds:
            # do step
            controller_output = self.controller.do_step(t_ctrl)
            self.building_model.actuate_HVAC_equipment(self.controller.HVAC_mode)
            step_status = (self.building_model.fmu.do_step(
                current_t=t_step_seconds,
                step_size=self.step_size_seconds, 
                new_step=True))
            # save data as row
            building_model_output = [self.building_model.fmu.get(k)[0] for k in self.building_model_output_keys]
            step_output = [t_step_seconds, step_status, t_ctrl] + controller_output + building_model_output
            output.append(step_output)
            # TODO add multizone support
            t_ctrl = self.calc_T_control(building_model_output)
            # step time forward
        # self.t_step_seconds += step_size

        print("="*80)
        print("Simulation finished.")
        print("="*80)

        return pd.DataFrame.from_records(output, columns=self.output_keys)




    

    # HVAC_mode = attr.ib(kw_only=True)
    # self.output_dir = os.path.join(os.environ["PACKAGE_DIR"], "data")



    # def __init__(self):
    #     self.control_model = ""
    #     self.bm = ""
    #     self.output_dir = os.path.join(os.environ["PACKAGE_DIR"], "data")

        