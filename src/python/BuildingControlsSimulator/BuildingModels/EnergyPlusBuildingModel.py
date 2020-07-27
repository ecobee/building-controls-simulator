# created by Tom Stesco tom.s@ecobee.com

import os
import logging

import pandas as pd
import attr
import numpy as np
from eppy import modeleditor
import pyfmi

from BuildingControlsSimulator.BuildingModels.BuildingModel import (
    BuildingModel,
)
from BuildingControlsSimulator.BuildingModels.IDFPreprocessor import (
    IDFPreprocessor,
)
from BuildingControlsSimulator.ControlModels.ControlModel import HVAC_modes
from BuildingControlsSimulator.ControlModels.ControlModel import ControlModel


logger = logging.getLogger(__name__)


@attr.s(kw_only=True)
class EnergyPlusBuildingModel(BuildingModel):
    """Abstract Base Class for building models


    """

    idf = attr.ib()
    weather_dir = attr.ib(default=os.environ.get("WEATHER_DIR"))
    # user must supply a weather file as either 1) full path, or 2) a file in self.idf_dir
    weather_file = attr.ib()
    fmu = attr.ib(default=None)
    T_heat_off = attr.ib(default=-60.0)
    T_heat_on = attr.ib(default=99.0)
    T_cool_off = attr.ib(default=99.0)
    T_cool_on = attr.ib(default=-60.0)

    cur_HVAC_mode = attr.ib(default=HVAC_modes.UNCONTROLLED)

    def __attrs_post_init__(self):
        # first make sure weather file exists
        if os.path.isfile(self.weather_file):
            self.weather_name = os.path.basename(self.weather_file)
        else:
            self.weather_name = self.weather_file
            self.weather_file = os.path.join(
                self.weather_dir, self.weather_name
            )
            if not os.path.isfile(self.weather_file):
                raise ValueError(f"""{self.weather_file} is not a file.""")

    @property
    def init_temperature(self):
        return self.idf.init_temperature

    def create_model_fmu(self):
        """
        """
        # TODO add validator for weather
        if not self.weather_file and self.weather_name:
            for r, d, f in os.walk(self.weather_dir):
                for fname in f:
                    if fname == self.weather_name:
                        self.weather_file = os.path.join(
                            self.weather_dir, self.weather_name
                        )
        elif not self.weather_file and not self.weather_name:
            raise ValueError(
                f"""Must supply valid weather file, 
                weather_file={self.weather_file} and weather_name={self.weather_name}"""
            )

        self.idf.make_fmu(weather=self.weather_file)
        # return pyfmi.load_fmu(fmu=self.idf.fmu_path)
        return self.idf.fmu_path

    def occupied_zones(self):
        """Gets occupiec zones from zones that have a tstat in them."""
        return [
            tstat.Zone_or_ZoneList_Name
            for tstat in self.idf.ep_idf.idfobjects[
                "zonecontrol:thermostat".upper()
            ]
        ]

    def actuate_HVAC_equipment_init_fmu(self, step_HVAC_mode, init_fmu):
        """
        """
        if self.cur_HVAC_mode != step_HVAC_mode:
            if step_HVAC_mode == HVAC_modes.SINGLE_HEATING_SETPOINT:
                init_fmu.set(
                    self.idf.FMU_control_type_name, int(step_HVAC_mode)
                )
                init_fmu.set(
                    self.idf.FMU_control_heating_stp_name, self.T_heat_on
                )
                init_fmu.set(
                    self.idf.FMU_control_cooling_stp_name, self.T_cool_off
                )
            elif step_HVAC_mode == HVAC_modes.SINGLE_COOLING_SETPOINT:
                init_fmu.set(
                    self.idf.FMU_control_type_name, int(step_HVAC_mode)
                )
                init_fmu.set(
                    self.idf.FMU_control_heating_stp_name, self.T_heat_off
                )
                init_fmu.set(
                    self.idf.FMU_control_cooling_stp_name, self.T_cool_on
                )

            elif step_HVAC_mode == HVAC_modes.UNCONTROLLED:
                init_fmu.set(
                    self.idf.FMU_control_type_name, int(step_HVAC_mode)
                )
                init_fmu.set(
                    self.idf.FMU_control_heating_stp_name, self.T_heat_off
                )
                init_fmu.set(
                    self.idf.FMU_control_cooling_stp_name, self.T_cool_off
                )

        self.cur_HVAC_mode = step_HVAC_mode

    def actuate_HVAC_equipment(self, step_HVAC_mode):
        """
        """
        if self.cur_HVAC_mode != step_HVAC_mode:
            if step_HVAC_mode == HVAC_modes.SINGLE_HEATING_SETPOINT:
                self.fmu.set(
                    self.idf.FMU_control_type_name, int(step_HVAC_mode)
                )
                self.fmu.set(
                    self.idf.FMU_control_heating_stp_name, self.T_heat_on
                )
                self.fmu.set(
                    self.idf.FMU_control_cooling_stp_name, self.T_cool_off
                )
            elif step_HVAC_mode == HVAC_modes.SINGLE_COOLING_SETPOINT:
                self.fmu.set(
                    self.idf.FMU_control_type_name, int(step_HVAC_mode)
                )
                self.fmu.set(
                    self.idf.FMU_control_heating_stp_name, self.T_heat_off
                )
                self.fmu.set(
                    self.idf.FMU_control_cooling_stp_name, self.T_cool_on
                )

            elif step_HVAC_mode == HVAC_modes.UNCONTROLLED:
                self.fmu.set(
                    self.idf.FMU_control_type_name, int(step_HVAC_mode)
                )
                self.fmu.set(
                    self.idf.FMU_control_heating_stp_name, self.T_heat_off
                )
                self.fmu.set(
                    self.idf.FMU_control_cooling_stp_name, self.T_cool_off
                )

        self.cur_HVAC_mode = step_HVAC_mode

    def initialize(self, start_time_seconds, final_time_seconds):
        """
        """
        self.fmu = pyfmi.load_fmu(fmu=self.idf.fmu_path)
        self.fmu.initialize(start_time_seconds, final_time_seconds)

    @staticmethod
    def make_directories():
        os.makedirs(os.environ.get("IDF_DIR"), exist_ok=True)
        os.makedirs(
            os.path.join(os.environ.get("IDF_DIR"), "preprocessed"),
            exist_ok=True,
        )
        os.makedirs(os.environ.get("FMU_DIR"), exist_ok=True)
        os.makedirs(os.environ.get("WEATHER_DIR"), exist_ok=True)
        os.makedirs(os.environ.get("OUTPUT_DIR"), exist_ok=True)
