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
import pyfmi

from BuildingControlsSimulator.DataClients.DataStates import STATES
from BuildingControlsSimulator.DataClients.DataSpec import Internal
from BuildingControlsSimulator.BuildingModels.BuildingModel import (
    BuildingModel,
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
    """Abstract Base Class for building models"""

    idf = attr.ib()
    weather_dir = attr.ib(default=os.environ.get("WEATHER_DIR"))
    # user must supply a weather file as either 1) full path, or 2) a file in self.idf_dir
    epw_path = attr.ib(default=None)
    fmi_version = attr.ib(type=float, default=1.0)
    timesteps_per_hour = attr.ib(default=12)
    fmu_dir = attr.ib(default=os.environ.get("FMU_DIR"))
    eplustofmu_path = attr.ib(default=os.environ.get("ENERGYPLUSTOFMUSCRIPT"))
    ext_dir = attr.ib(default=os.environ.get("EXT_DIR"))
    fmu_output = attr.ib(factory=dict)
    output = attr.ib(factory=dict)
    step_output = attr.ib(factory=dict)
    init_humidity = attr.ib(default=50.0)
    init_temperature = attr.ib(default=21.0)
    fmu = attr.ib(default=None)

    # for reference on how attr defaults wor for mutable types (e.g. list) see:
    # https://www.attrs.org/en/stable/init.html#defaults
    input_states = attr.ib()
    output_states = attr.ib()

    @input_states.default
    def get_input_states(self):
        return [
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

    @output_states.default
    def get_output_states(self):
        return [
            STATES.THERMOSTAT_TEMPERATURE,
            STATES.THERMOSTAT_HUMIDITY,
            STATES.THERMOSTAT_MOTION,
        ]

    def __attrs_post_init__(self):
        pass

    @property
    def init_temperature(self):
        return self.idf.init_temperature

    @property
    def init_fmu_name(self):
        init_fmu_name = os.path.splitext(self.idf.idf_prep_name)[0]
        # add automatic conversion rules for fmu naming
        idf_bad_chars = [" ", "-", "+", "."]
        for c in idf_bad_chars:
            init_fmu_name = init_fmu_name.replace(c, "_")

        if init_fmu_name[0].isdigit():
            init_fmu_name = "f_" + init_fmu_name

        init_fmu_name = init_fmu_name + ".fmu"

        return init_fmu_name

    @property
    def fmu_name(self):
        if not self.epw_path:
            raise ValueError(
                "Cannot name FMU without specifying weather file."
            )

        # the full fmu name is unique per combination of:
        # 1. IDF file
        # 2. weather service used
        # 3. thermostat ID
        # this is because the simulation weather is compiled into the FMU
        fmu_name = (
            self.idf.idf_prep_name
            + "_"
            + os.path.splitext(os.path.basename(self.epw_path))[0]
        )
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
        self.idf.init_temperature = self.init_temperature
        self.idf.init_humidity = self.init_humidity
        self.idf.preprocess(preprocess_check=preprocess_check)

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
            os.path.join(os.getcwd(), self.init_fmu_name),
            self.fmu_path,
        )

        return self.fmu_path

    def initialize(
        self, start_utc, t_start, t_end, t_step, categories_dict={}
    ):
        """"""
        logger.info(f"Initializing EnergyPlusBuildingModel: {self.fmu_path}")
        self.allocate_output_memory(t_start, t_end, t_step, categories_dict)
        self.init_step_output()
        self.fmu = pyfmi.load_fmu(fmu=self.fmu_path)
        # initialize for extra step to keep whole days for final period at 23:55
        self.fmu.initialize(t_start, t_end + t_step)

    def tear_down(self):
        """tear down FMU"""
        # Note: calling fmu.terminate() and fmu.free_instance() should not be needed
        # this causes segfault sometimes
        # energyplus FMU should take care of its own destruction
        pass

    def init_step_output(self):
        self.step_output[STATES.THERMOSTAT_TEMPERATURE] = self.init_temperature
        self.step_output[STATES.THERMOSTAT_HUMIDITY] = self.init_humidity
        self.step_output[STATES.THERMOSTAT_MOTION] = False

    def allocate_output_memory(self, t_start, t_end, t_step, categories_dict):
        """preallocate output memory as numpy arrays to speed up simulation"""
        # reset output memory
        self.output = {}
        self.fmu_output = {}

        self.output = {
            STATES.SIMULATION_TIME: np.arange(
                t_start, t_end + t_step, t_step, dtype="int64"
            )
        }
        n_s = len(self.output[STATES.SIMULATION_TIME])

        # add output state variables
        for state in self.output_states:
            if Internal.full.spec[state]["dtype"] == "category":
                self.output[state] = pd.Series(
                    pd.Categorical(
                        pd.Series(index=np.arange(n_s)),
                        categories=categories_dict[state],
                    )
                )
            else:
                (
                    np_default_value,
                    np_dtype,
                ) = Conversions.numpy_down_cast_default_value_dtype(
                    Internal.full.spec[state]["dtype"]
                )
                self.output[state] = np.full(
                    n_s,
                    np_default_value,
                    dtype=np_dtype,
                )

        # add fmu state variables
        self.fmu_output[STATES.STEP_STATUS] = np.full(n_s, False, dtype="bool")
        self.fmu_output[STATES.SIMULATION_TIME] = self.output[
            STATES.SIMULATION_TIME
        ]

        for k, v in self.idf.output_spec.items():
            (
                np_default_value,
                np_dtype,
            ) = Conversions.numpy_down_cast_default_value_dtype(v["dtype"])
            self.fmu_output[k] = np.full(n_s, np_default_value, dtype=np_dtype)

        # set current time
        self.current_time = t_start
        self.current_t_idx = 0

    def do_step(
        self,
        t_start,
        t_step,
        step_control_input,
        step_sensor_input,
        step_weather_input,
    ):
        """
        Simulate controller time step.
        Before building model step `HVAC_mode` is the HVAC_mode for the step
        """
        # advance current time
        self.current_t_start = t_start

        # set input
        self.actuate_HVAC_equipment(step_control_input)

        status = self.fmu.do_step(
            current_t=t_start,
            step_size=t_step,
            new_step=True,
        )
        self.update_output(status, step_sensor_input)

        # finally increment t_idx
        self.current_t_idx += 1

    def update_output(self, status, step_sensor_input):
        """Update internal output obj for current_t_idx with fmu output."""

        self.fmu_output[STATES.STEP_STATUS][self.current_t_idx] = status

        # get fmi zone output
        for k, v in self.idf.output_spec.items():
            self.fmu_output[k][self.current_t_idx] = self.fmu.get(k)[0]

        # map fmu output to model output
        self.output[STATES.THERMOSTAT_TEMPERATURE][
            self.current_t_idx
        ] = self.get_tstat_temperature()

        self.output[STATES.THERMOSTAT_HUMIDITY][
            self.current_t_idx
        ] = Conversions.relative_humidity_from_dewpoint(
            temperature=self.output[STATES.THERMOSTAT_TEMPERATURE][
                self.current_t_idx
            ],
            dewpoint=self.get_tstat_dewpoint(),
        )
        # pass through outputs
        self.output[STATES.THERMOSTAT_MOTION][
            self.current_t_idx
        ] = step_sensor_input[STATES.THERMOSTAT_MOTION]

        # get step_output
        for state in self.output_states:
            self.step_output[state] = self.output[state][self.current_t_idx]

    def get_fmu_output_keys(self, eplus_key):
        return [
            k
            for k, v in self.idf.output_spec.items()
            if v["eplus_name"] == eplus_key
        ]

    def get_mean_temperature(self):
        return np.mean(
            [
                self.fmu_output[k][self.current_t_idx]
                for k in self.get_fmu_output_keys("Zone Air Temperature")
            ]
        )

    def get_tstat_temperature(self):
        """tstat temperature is air temperature from zone containing tstat"""
        fmu_name = f"{self.idf.thermostat_zone}_zone_air_temperature"
        return self.fmu_output[fmu_name][self.current_t_idx]

    def get_rs_temperature(self):
        pass

    def get_tstat_dewpoint(self):
        """tstat temperature is air temperature from zone containing tstat"""
        fmu_name = (
            f"{self.idf.thermostat_zone}_zone_mean_air_dewpoint_temperature"
        )
        return self.fmu_output[fmu_name][self.current_t_idx]

    def get_mean_dewpoint(self):
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
        T_cool_on = -60.0

        # map input states to specific actuation within EPlus model
        run_heat = bool(
            (step_control_input[STATES.AUXHEAT1] > 0)
            or (step_control_input[STATES.AUXHEAT2] > 0)
            or (step_control_input[STATES.AUXHEAT3] > 0)
            or (step_control_input[STATES.COMPHEAT1] > 0)
            or (step_control_input[STATES.COMPHEAT2] > 0)
        )

        run_cool = bool(
            (step_control_input[STATES.COMPCOOL1] > 0)
            or (step_control_input[STATES.COMPCOOL2] > 0)
        )

        if run_heat and run_cool:
            logger.error("Cannot heat and cool at same time.")
        elif run_heat:
            self.fmu.set(
                self.idf.FMU_control_type_name,
                int(EPLUS_THERMOSTAT_MODES.SINGLE_HEATING_SETPOINT),
            )
            self.fmu.set(self.idf.FMU_control_heating_stp_name, T_heat_on)
            self.fmu.set(self.idf.FMU_control_cooling_stp_name, T_cool_off)
        elif run_cool:
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
