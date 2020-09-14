# created by Tom Stesco tom.s@ecobee.com

import os
import logging
import subprocess
import shlex
import shutil

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
    epw_path = attr.ib(default=None)
    fmi_version = attr.ib(type=float, default=1.0)
    timesteps_per_hour = attr.ib(default=12)
    fmu_dir = attr.ib(default=os.environ.get("FMU_DIR"))
    eplustofmu_path = attr.ib(default=os.environ.get("ENERGYPLUSTOFMUSCRIPT"))
    # ep_version = attr.ib(default=os.environ.get("ENERGYPLUS_INSTALL_VERSION"))
    ext_dir = attr.ib(default=os.environ.get("EXT_DIR"))

    building_input_spec = attr.ib(
        default={
            "HeatStageOne": {"input_name": "HeatStageOne", "dtype": "bool",},
            "HeatStageTwo": {"input_name": "HeatStageTwo", "dtype": "bool",},
            "HeatStageThree": {
                "input_name": "HeatStageThree",
                "dtype": "bool",
            },
            "CompressorCoolStageOne": {
                "input_name": "CompressorCoolStageOne",
                "dtype": "bool",
            },
            "CompressorCoolStageTwo": {
                "input_name": "CompressorCoolStageTwo",
                "dtype": "bool",
            },
            "CompressorHeatStageOne": {
                "input_name": "CompressorHeatStageOne",
                "dtype": "bool",
            },
            "CompressorHeatStageTwo": {
                "input_name": "CompressorHeatStageTwo",
                "dtype": "bool",
            },
            "FanStageOne": {"input_name": "FanStageOne", "dtype": "bool",},
            "FanStageTwo": {"input_name": "FanStageTwo", "dtype": "bool",},
            "FanStageThree": {"input_name": "FanStageThree", "dtype": "bool",},
        }
    )
    # keys with "output_name" == None are not part of external output
    building_output_spec = attr.ib(
        default={
            "TstatTemperature": {
                "output_name": "TstatTemperature",
                "dtype": "float32",
            },
            "TstatHumidity": {
                "output_name": "TstatHumidity",
                "dtype": "float32",
            },
            "Status": {"output_name": None, "dtype": "bool",},
        }
    )

    fmu = attr.ib(default=None)
    T_heat_off = attr.ib(default=-60.0)
    T_heat_on = attr.ib(default=99.0)
    T_cool_off = attr.ib(default=99.0)
    T_cool_on = attr.ib(default=-60.0)

    cur_HVAC_mode = attr.ib(default=HVAC_modes.UNCONTROLLED)

    def __attrs_post_init__(self):
        pass

    @property
    def init_temperature(self):
        return self.idf.init_temperature

    @property
    def fmu_name(self):
        fmu_name = os.path.splitext(self.idf.idf_prep_name)[0]
        # add automatic conversion rules for fmu naming
        idf_bad_chars = [" ", "-", "+", "."]
        for c in idf_bad_chars:
            fmu_name = fmu_name.replace(c, "_")

        if fmu_name[0].isdigit():
            fmu_name = "f_" + fmu_name

        fmu_name = fmu_name + ".fmu"

        return fmu_name

    @property
    def fmu_path(self):
        return os.path.join(self.fmu_dir, self.fmu_name)

    def create_model_fmu(self, epw_path=None):
        """make the fmu

        Calls FMU model generation script from https://github.com/lbl-srg/EnergyPlusToFMU.
        This script litters temporary files of fixed names which get clobbered
        if running in parallel. Need to fix scripts to be able to run in parallel.
        """
        if epw_path:
            self.epw_path = epw_path

        elif not self.epw_path:
            raise ValueError(
                f"Must supply valid weather file, epw_path={self.epw_path}"
            )
        self.idf.timesteps_per_hour = self.timesteps_per_hour
        self.idf.preprocess()

        cmd = f"python2.7 {self.eplustofmu_path}"
        cmd += f" -i {self.idf.idd_path}"
        cmd += f" -w {self.epw_path}"
        cmd += f" -a {self.fmi_version}"
        cmd += f" -d {self.idf.idf_prep_path}"

        proc = subprocess.run(shlex.split(cmd), stdout=subprocess.PIPE)
        if not proc.stdout:
            raise ValueError(
                f"Empty STDOUT. Invalid EnergyPlusToFMU cmd={cmd}"
            )

        # EnergyPlusToFMU puts fmu in cwd always, move out of cwd
        shutil.move(
            os.path.join(os.getcwd(), self.fmu_name), self.fmu_path,
        )
        # check FMI compliance
        # -h specifies the step size in seconds, -s is the stop time in seconds.
        # Stop time must be a multiple of 86400.
        # The step size needs to be the same as the .idf file specifies

        cmd = (
            "yes |"
            f" {self.ext_dir}/FMUComplianceChecker/fmuCheck.linux64"
            f" -h {self.timesteps_per_hour}"
            " -s 172800"
            f" {self.fmu_path}"
        )
        # subprocess.run(cmd.split(), stdout=subprocess.PIPE)
        # if not proc.stdout:
        #     raise ValueError(f"Empty STDOUT. Invalid EnergyPlusToFMU cmd={cmd}")

        return self.fmu_path

    def initialize(self, t_start, t_end, ts):
        """
        """
        self.fmu = pyfmi.load_fmu(fmu=self.idf.fmu_path)
        self.fmu.initialize(t_start, t_end)

        # allocate output memory
        time = np.arange(t_start, t_end, ts, dtype="int64")
        n_s = len(time)

        self.output = {}

        # add fmu state variables
        for k, v, in self.controller_output_spec.items():
            if v["dtype"] == "bool":
                self.output[k] = np.full(n_s, False, dtype="bool")
            elif v["dtype"] == "float32":
                self.output[k] = np.full(n_s, -999, dtype="float32")
            else:
                raise ValueError(
                    "Unsupported output_map dtype: {}".format(v["dtype"])
                )

        self.output["time"] = time
        self.output["status"] = np.full(n_s, False, dtype="bool")

        # set current time
        self.current_time = t_start
        self.current_t_end = t_end
        self.current_t_idx = 0

    def do_step(
        self,
        t_start,
        t_end,
        step_control_input,
        step_weather_input,
        step_occupancy_input,
    ):
        """
        Simulate controller time step.
        Before building model step `HVAC_mode` is the HVAC_mode for the step
        """
        # advance current time
        self.current_t_start = t_start
        self.current_t_end = t_end

        # set input

        # new_step=True ?
        status = self.fmu.do_step(t_start, t_end)
        self.update_output(status)

        # finally increment t_idx
        self.current_t_idx += 1

    def occupied_zones(self):
        """Gets occupied zones from zones that have a tstat in them."""
        return [
            tstat.Zone_or_ZoneList_Name
            for tstat in self.idf.ep_idf.idfobjects[
                "zonecontrol:thermostat".upper()
            ]
        ]

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
