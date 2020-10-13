# created by Tom Stesco tom.s@ecobee.com

import os
import logging
import time

import pandas as pd
import numpy as np
import attr

from BuildingControlsSimulator.DataClients.DataStates import STATES
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
    """Converts IDFs (Input Data Files) for EnergyPlus into working IDFs."""

    building_model = attr.ib()
    controller_model = attr.ib()
    data_client = attr.ib()
    config = attr.ib()
    output_data_dir = attr.ib(
        default=os.path.join(os.environ.get("OUTPUT_DIR"), "data")
    )
    output_plot_dir = attr.ib(
        default=os.path.join(os.environ.get("OUTPUT_DIR"), "plot")
    )
    start_utc = attr.ib(default=None)
    end_utc = attr.ib(default=None)
    output = attr.ib(default=None)
    full_input = attr.ib(default=None)

    def __attrs_post_init__(self):
        """validate input/output specs
        next input must be minimally satisfied by previous output
        """

        # get all data states that can be input to each model
        available_data_states = [
            v["internal_state"]
            for k, v in self.data_client.source.data_spec.hvac.spec.items()
        ]
        available_data_states += [
            v["internal_state"]
            for k, v in self.data_client.source.data_spec.sensors.spec.items()
        ]
        available_data_states += [
            v["internal_state"]
            for k, v in self.data_client.source.data_spec.weather.spec.items()
        ]

        missing_controller_output_states = [
            k
            for k in self.building_model.input_states
            if k
            not in self.controller_model.output_states + available_data_states
        ]
        if any(missing_controller_output_states):
            raise ValueError(
                f"type(controller_model)={type(self.controller_model)}\n",
                f"Missing controller output keys: {missing_controller_output_states}\n",
            )

        missing_building_output_keys = [
            k
            for k in self.controller_model.input_states
            if k
            not in self.building_model.output_states + available_data_states
        ]
        if any(missing_building_output_keys):
            raise ValueError(
                f"type(building_model)={type(self.building_model)}\n",
                f"Missing building model output keys: {missing_building_output_keys}\n",
            )

    @property
    def steps_per_hour(self):
        return int(60 / self.config.step_size_minutes)

    @property
    def step_size_seconds(self):
        return int(self.config.step_size_minutes * 60)

    @property
    def start_time_seconds(self):
        t_offset = self.start_utc - pd.Timestamp(
            year=self.start_utc.year,
            month=1,
            day=1,
            tz="UTC",
        )
        return int(t_offset.total_seconds())

    @property
    def final_time_seconds(self):
        t_offset = self.end_utc - pd.Timestamp(
            year=self.end_utc.year,
            month=1,
            day=1,
            tz="UTC",
        )
        return int(t_offset.total_seconds())

    @property
    def output_keys(self):
        return (
            self.simulator_output_keys
            + self.controller_model.output_keys
            + self.building_model.output_keys
        )

    @property
    def building_model_output_keys(self):
        return self.building_model.fmu.get_model_variables().keys()

    def create_models(self, preprocess_check=False):
        return self.building_model.create_model_fmu(
            epw_path=self.data_client.weather.epw_path,
            preprocess_check=preprocess_check,
        )

    def initialize(self):
        """initialize sub-system models and memory for simulation"""
        # get simulation time from data client
        self.start_utc = self.data_client.start_utc
        self.end_utc = self.data_client.end_utc

        if not self.start_utc:
            raise ValueError("start_utc is None.")

        if not self.end_utc:
            raise ValueError("end_utc is None.")

        self.building_model.initialize(
            start_utc=self.start_utc,
            t_start=self.start_time_seconds,
            t_end=self.final_time_seconds,
            t_step=self.step_size_seconds,
            categories_dict=self.data_client.hvac.get_categories_dict(),
        )
        self.controller_model.initialize(
            start_utc=self.start_utc,
            t_start=self.start_time_seconds,
            t_end=self.final_time_seconds,
            t_step=self.step_size_seconds,
            categories_dict=self.data_client.hvac.get_categories_dict(),
        )

        self.allocate_memory()

    def allocate_memory(self):
        """Allocate memory for simulation output"""
        self.output = {}

    def tear_down(self):
        logger.info("Tearing down co-simulation models")
        self.building_model.tear_down()
        self.controller_model.tear_down()

    def determine_settings(self, t_idx):
        """Ensure settings are correct for given time step."""
        _time = self.data_client.hvac.iloc[t_idx][STATES.DATE_TIME]
        new_settings = {}
        if _time in self.data_client.hvac.change_points_schedule.keys():
            new_settings[
                "schedules"
            ] = self.data_client.hvac.change_points_schedule[_time]
        if _time in self.data_client.hvac.change_points_comfort_prefs.keys():
            new_settings[
                "setpoints"
            ] = self.data_client.hvac.change_points_comfort_prefs[_time]

        if new_settings:
            self.controller_model.change_settings(new_settings)

    def run(self, local=True):
        """Main co-simulation loop"""
        logger.info("Initializing co-simulation models")
        self.initialize()

        logger.info(
            f"Running co-simulation from {self.start_utc} to {self.end_utc}"
        )
        _sim_start_wall_time = time.perf_counter()
        _sim_start_proc_time = time.process_time()
        _sim_time = np.arange(
            self.start_time_seconds,
            self.final_time_seconds + self.step_size_seconds,
            self.step_size_seconds,
            dtype="int64",
        )
        for i in range(0, len(_sim_time)):
            self.determine_settings(t_idx=i)
            self.controller_model.do_step(
                t_start=_sim_time[i],
                t_step=self.step_size_seconds,
                step_hvac_input=self.data_client.hvac.data.iloc[i],
                step_sensor_input=self.building_model.step_output,
                step_weather_input=self.data_client.weather.data.iloc[i],
            )
            self.building_model.do_step(
                t_start=_sim_time[i],
                t_step=self.step_size_seconds,
                step_control_input=self.controller_model.step_output,
                step_sensor_input=self.data_client.sensors.data.iloc[i],
                step_weather_input=self.data_client.weather.data.iloc[i],
            )

        # t_ctrl output is time-shifted to make runtime integral over preceeding timestep
        # final timestep controller output will be repeated
        # TODO: recompute t_ctrl given final state
        self.controller_model.output[STATES.TEMPERATURE_CTRL][
            0:-1
        ] = self.controller_model.output[STATES.TEMPERATURE_CTRL][1:]

        logger.info(
            "Finished co-simulation\n"
            + f"Elapsed time: {time.perf_counter() - _sim_start_wall_time} seconds\n"
            + f"Process time: {time.process_time() - _sim_start_proc_time} seconds"
        )

        self.tear_down()

        # convert output to dataframe
        self.output = pd.DataFrame.from_dict(
            {
                STATES.DATE_TIME: self.data_client.hvac.data[
                    STATES.DATE_TIME
                ].to_numpy(),
                **self.controller_model.output,
                **self.building_model.output,
            }
        )

        # only consider data within data periods as output
        _mask = self.output[STATES.DATE_TIME].isnull()
        for dp_start, dp_end in self.data_client.full_data_periods:
            _mask = _mask | (self.output[STATES.DATE_TIME] >= dp_start) & (
                self.output[STATES.DATE_TIME] < dp_end
            )

        self.output = self.output[_mask]

        self.full_input = self.get_full_input()[_mask]

    def get_full_input(self):
        full_input = pd.concat(
            [
                self.data_client.hvac.data,
                self.data_client.sensors.data,
                self.data_client.weather.data,
            ],
            axis="columns",
        )
        # drop duplicated datetime columns
        full_input = full_input.loc[:, ~full_input.columns.duplicated()]
        return full_input

    def show_plots(self):
        output_analysis = OutputAnalysis(df=self.output_df)
        # output_analysis.postprocess()
        output_analysis.diagnostic_plot(show=True)
        # output_analysis.thermal_plot(show=True)
        # output_analysis.power_plot(show=True)
        # output_analysis.control_actuation_plot(show=True)
