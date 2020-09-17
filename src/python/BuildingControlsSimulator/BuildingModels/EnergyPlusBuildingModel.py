# created by Tom Stesco tom.s@ecobee.com

import os
import logging
import subprocess
import shlex
import shutil
from enum import IntEnum

import pandas as pd
import attr
import numpy as np
from eppy import modeleditor
import pyfmi

from BuildingControlsSimulator.DataClients.DataStates import STATES
from BuildingControlsSimulator.BuildingModels.BuildingModel import (
    BuildingModel,
)
from BuildingControlsSimulator.BuildingModels.IDFPreprocessor import (
    IDFPreprocessor,
)

from BuildingControlsSimulator.ControlModels.ControlModel import ControlModel
from BuildingControlsSimulator.Conversions.Conversions import Conversions


logger = logging.getLogger(__name__)


class EPLUS_THERMOSTAT_MODES(IntEnum):
    """
    0 - Uncontrolled (No specification or default)
    1 - Single Heating Setpoint
    2 - Single Cooling SetPoint
    3 - Single Heating Cooling Setpoint
    4 - Dual Setpoint with Deadband (Heating and Cooling)
    """

    UNCONTROLLED = 0
    SINGLE_HEATING_SETPOINT = 1
    SINGLE_COOLING_SETPOINT = 2
    DUAL_HEATING_COOLING_SETPOINT = 3


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
    ext_dir = attr.ib(default=os.environ.get("EXT_DIR"))
    fmu_output = attr.ib(default={})
    output = attr.ib(default={})
    step_size_seconds = attr.ib(default=None)

    input_states = attr.ib(
        default=[
            STATES.AUXHEAT1,
            STATES.AUXHEAT2,
            STATES.AUXHEAT3,
            STATES.COMPCOOL1,
            STATES.COMPCOOL2,
            STATES.COMPHEAT1,
            STATES.COMPHEAT2,
            STATES.FAN_STAGE_ONE,
            STATES.FAN_STAGE_TWO,
            STATES.FAN_STAGE_THREE,
        ]
    )
    # keys with "output_name" == None are not part of external output
    output_states = attr.ib(
        default=[
            STATES.TEMPERATURE_CTRL,
            STATES.TEMPERATURE_STP_COOL,
            STATES.TEMPERATURE_STP_HEAT,
        ]
    )

    fmu_spec = attr.ib(
        default={"Status": {"output_name": None, "dtype": "bool",},}
    )

    fmu = attr.ib(default=None)

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

    def create_model_fmu(self, epw_path=None, preprocess_check=False):
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
        self.idf.preprocess(preprocess_check=False)

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

    def initialize(self, t_start, t_end, t_step):
        """
        """
        self.fmu = pyfmi.load_fmu(fmu=self.fmu_path)
        self.fmu.initialize(t_start, t_end)

        self.allocate_output_memory(t_start, t_end, t_step)

    def allocate_output_memory(self, t_start, t_end, t_step):
        """preallocate output memory as numpy arrays to speed up simulation
        """
        time = np.arange(t_start, t_end, t_step, dtype="int64")
        n_s = len(time)

        self.output = {}

        # add output state variables
        for k, v, in self.output_spec.items():
            if v["dtype"] == "bool":
                self.output[k] = np.full(n_s, False, dtype="bool")
            elif v["dtype"] == "float32":
                self.output[k] = np.full(n_s, -999, dtype="float32")
            else:
                raise ValueError(
                    "Unsupported output_map dtype: {}".format(v["dtype"])
                )

        # add fmu state variables
        self.fmu_output["Status"] = np.full(n_s, False, dtype="bool")
        self.fmu_output["time"] = time
        for k, v, in self.idf.output_spec.items():
            if v["dtype"] == "bool":
                self.fmu_output[k] = np.full(n_s, False, dtype="bool")
            elif v["dtype"] == "float32":
                self.fmu_output[k] = np.full(n_s, -999, dtype="float32")
            else:
                raise ValueError(
                    "Unsupported output_map dtype: {}".format(v["dtype"])
                )

        self.output["time"] = time
        # self.output["status"] = np.full(n_s, False, dtype="bool")

        # set current time
        self.current_time = t_start
        self.current_t_end = t_end
        self.current_t_idx = 0

    def do_step(
        self,
        t_start,
        t_step,
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
        # self.current_t_end = t_end

        # set input
        self.actuate_HVAC_equipment(step_control_input)

        # new_step=True ?
        status = self.fmu.do_step(
            current_t=t_start, step_size=t_step, new_step=True,
        )
        self.update_output(status)

        # finally increment t_idx
        self.current_t_idx += 1

    def update_output(self, status):
        """Update internal output obj for current_t_idx with fmu output."""

        # first get fmi zone output
        for k in self.idf.output_spec.keys():
            self.fmu_output[k][self.current_t_idx] = self.fmu.get(k)[0]

        self.output["tstat_temperature"][
            self.current_t_idx
        ] = self.get_tstat_temperature()

        self.output["tstat_humidity"][
            self.current_t_idx
        ] = Conversions.relative_humidity_from_dewpoint(
            temperature=self.output["tstat_temperature"][self.current_t_idx],
            dewpoint=self.get_tstat_dewpoint(),
        )
        # map fmu output to model output

    def get_fmu_output_keys(self, eplus_key):
        return [
            k
            for k, v in self.idf.output_spec.items()
            if v["eplus_name"] == eplus_key
        ]

    def get_tstat_temperature(self):
        return np.mean(
            [
                self.fmu_output[k][self.current_t_idx]
                for k in self.get_fmu_output_keys("Zone Air Temperature")
            ]
        )

    def get_tstat_dewpoint(self):
        return np.mean(
            [
                self.fmu_output[k][self.current_t_idx]
                for k in self.get_fmu_output_keys(
                    "Zone Mean Air Dewpoint Temperature"
                )
            ]
        )

    def actuate_HVAC_equipment(self, step_control_input):
        """
        passes actuation to building model with minimal validation.
        """
        T_heat_off = -60.0
        T_heat_on = 99.0
        T_cool_off = 99.0
        T_cool_on = 60.0

        if (
            step_control_input["heat_stage_one"]
            and step_control_input["compressor_cool_stage_one"]
        ):
            info.error(
                "Cannot heat and cool at same time. "
                f"heat_stage_one={step_control_input['heat_stage_one']} "
                f"compressor_cool_stage_one={step_control_input['compressor_cool_stage_one']}"
            )

        if step_control_input["heat_stage_one"]:
            self.fmu.set(
                self.idf.FMU_control_type_name,
                int(EPLUS_THERMOSTAT_MODES.SINGLE_HEATING_SETPOINT),
            )
            self.fmu.set(self.idf.FMU_control_heating_stp_name, T_heat_on)
            self.fmu.set(self.idf.FMU_control_cooling_stp_name, T_cool_off)
        elif step_control_input["compressor_cool_stage_one"]:
            self.fmu.set(
                self.idf.FMU_control_type_name,
                int(EPLUS_THERMOSTAT_MODES.SINGLE_COOLING_SETPOINT),
            )
            self.fmu.set(self.idf.FMU_control_heating_stp_name, T_heat_off)
            self.fmu.set(self.idf.FMU_control_cooling_stp_name, T_cool_on)

        else:
            self.fmu.set(
                self.idf.FMU_control_type_name,
                int(EPLUS_THERMOSTAT_MODES.UNCONTROLLED),
            )
            self.fmu.set(self.idf.FMU_control_heating_stp_name, T_heat_off)
            self.fmu.set(self.idf.FMU_control_cooling_stp_name, T_cool_off)

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
