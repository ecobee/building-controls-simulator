# created by Tom Stesco tom.s@ecobee.com

import os
import subprocess
import shlex
import shutil

import pandas as pd
import attr
import numpy as np
from eppy import modeleditor
import pyfmi

from BuildingControlSimulator.BuildingModels.BuildingModel import BuildingModel
from BuildingControlSimulator.BuildingModels.IDFPreprocessor import IDFPreprocessor
from BuildingControlSimulator.ControlModels.ControlModel import HVAC_modes
from BuildingControlSimulator.ControlModels.ControlModel import ControlModel

@attr.s
class EnergyPlusBuildingModel(BuildingModel):
    """Abstract Base Class for building models


    """
    idf = attr.ib(kw_only=True)

    weather_dir = attr.ib(default=os.environ["WEATHER_DIR"])
    # TODO add validator for weather
    weather_path = attr.ib(default=None)
    weather_name = attr.ib(default=None)
    fmu = attr.ib(default=None)


    T_heat_off = attr.ib(default=-60.0)
    T_heat_on = attr.ib(default=99.0)
    T_cool_off = attr.ib(default=99.0)
    T_cool_on = attr.ib(default=-60.0)

    cur_HVAC_mode = attr.ib(default=HVAC_modes.UNCONTROLLED)
    # step_HVAC_mode = attr.ib(default=HVAC_modes.UNCONTROLLED)

    # @classmethod
    # def from_idf(cls):
    #     pass

    @property
    def init_temperature(self):
        return self.idf.init_temperature
    

    # def preprocess(self):
    #     """
    #     """
    #     self.idf.preprocess(steps_per_hour)

    def create_model_fmu(self):
        
        # TODO add validator for weather

        if not self.weather_path and self.weather_name:
            for r, d, f in os.walk(self.weather_dir):
                for fname in f:
                    if fname == self.weather_name:
                        self.weather_path = os.path.join(self.weather_dir, self.weather_name)
        else:
            raise ValueError(f"""Must supply valid weather file, 
                weather_path={self.weather_path} and weather_name={self.weather_name}""")

        self.idf.make_fmu(weather_path=self.weather_path)
        return pyfmi.load_fmu(fmu=self.idf.fmu_path)


    def actuate_HVAC_equipment(self, step_HVAC_mode):
        """
        """
        if self.cur_HVAC_mode != step_HVAC_mode:
            if step_HVAC_mode == HVAC_modes.SINGLE_HEATING_SETPOINT:
                self.fmu.set(self.idf.FMU_control_type_name, int(step_HVAC_mode))
                self.fmu.set(self.idf.FMU_control_heating_stp_name, self.T_heat_on)
                self.fmu.set(self.idf.FMU_control_cooling_stp_name, self.T_cool_off)
            elif step_HVAC_mode == HVAC_modes.SINGLE_COOLING_SETPOINT:
                self.fmu.set(self.idf.FMU_control_type_name, int(step_HVAC_mode))
                self.fmu.set(self.idf.FMU_control_heating_stp_name, self.T_heat_off)
                self.fmu.set(self.idf.FMU_control_cooling_stp_name, self.T_cool_on)

            elif step_HVAC_mode == HVAC_modes.UNCONTROLLED:
                self.fmu.set(self.idf.FMU_control_type_name, int(step_HVAC_mode))
                self.fmu.set(self.idf.FMU_control_heating_stp_name, self.T_heat_off)
                self.fmu.set(self.idf.FMU_control_cooling_stp_name, self.T_cool_off)

        self.cur_HVAC_mode = step_HVAC_mode

    # def do_step(self):

    def initialize(self, start_time_seconds, final_time_seconds):
        """
        """
        self.fmu = self.create_model_fmu()
        print("Model init starting ...")
        self.fmu.initialize(start_time_seconds, final_time_seconds)
        print("Complete.")

