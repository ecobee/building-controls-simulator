# created by Tom Stesco tom.s@ecobee.com

import os
import logging
import time

import pandas as pd
import numpy as np
import attr

from BuildingControlsSimulator.DataClients.DataStates import STATES
from BuildingControlsSimulator.OutputAnalysis.OutputAnalysis import (
    OutputAnalysis,
)

logger = logging.getLogger(__name__)


@attr.s(kw_only=True)
class Simulation:
    """Converts IDFs (Input Data Files) for EnergyPlus into working IDFs."""

    building_model = attr.ib()
    state_estimator_model = attr.ib()
    controller_model = attr.ib()
    data_client = attr.ib()
    config = attr.ib()
    sim_run_identifier = attr.ib()
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
            for k, v in self.data_client.source.data_spec.datetime.spec.items()
        ]
        available_data_states += [
            v["internal_state"]
            for k, v in self.data_client.source.data_spec.thermostat.spec.items()
        ]
        available_data_states += [
            v["internal_state"]
            for k, v in self.data_client.source.data_spec.equipment.spec.items()
        ]
        available_data_states += [
            v["internal_state"]
            for k, v in self.data_client.source.data_spec.sensors.spec.items()
        ]
        available_data_states += [
            v["internal_state"]
            for k, v in self.data_client.source.data_spec.weather.spec.items()
        ]

        missing_state_estimator_output_states = [
            k
            for k in self.controller_model.input_states
            if k not in self.state_estimator_model.output_states + available_data_states
        ]
        if any(missing_state_estimator_output_states):
            raise ValueError(
                f"type(state_estimator_model)={type(self.state_estimator_model)}\n",
                f"Missing state_estimator output keys: {missing_state_estimator_output_states}\n",
            )

        missing_controller_output_states = [
            k
            for k in self.controller_model.input_states
            if k not in self.state_estimator_model.output_states + available_data_states
        ]
        if any(missing_controller_output_states):
            raise ValueError(
                f"type(controller_model)={type(self.controller_model)}\n",
                f"Missing controller output keys: {missing_controller_output_states}\n",
            )

        missing_building_output_keys = [
            k
            for k in self.state_estimator_model.input_states
            if k not in self.building_model.output_states + available_data_states
        ]
        if any(missing_building_output_keys):
            raise ValueError(
                f"type(building_model)={type(self.building_model)}\n",
                f"Missing building model output keys: {missing_building_output_keys}\n",
            )

    @property
    def step_size_seconds(self):
        return int(self.config["sim_step_size_seconds"])

    @property
    def output_step_size_seconds(self):
        return int(self.config["output_step_size_seconds"])

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

    @property
    def sim_name(self):
        _prefix = "sim"
        _sim_run_identifier = self.sim_run_identifier
        _data_source = self.data_client.source.source_name
        _identifier = self.data_client.sim_config["identifier"]
        _building_model_name = self.building_model.get_model_name()
        _controller_model_name = self.controller_model.get_model_name()

        _sim_name = "_".join(
            [
                _prefix,
                _sim_run_identifier,
                _data_source,
                _identifier,
                _building_model_name,
                _controller_model_name,
            ]
        )
        # safely remove any errant . characters breaking extension handling
        _sim_name.replace(".", "_")
        return _sim_name

    def create_models(self, preprocess_check=False):
        # TODO: only have the building model that requires dynamic building
        # when other models exist that must be created generalize this interface
        self.building_model.step_size_seconds = self.step_size_seconds
        self.building_model.create_model_fmu(
            sim_config=self.config,
            weather_channel=self.data_client.weather,
            datetime_channel=self.data_client.datetime,
            preprocess_check=preprocess_check,
        )

    def initialize(self, data_spec):
        """initialize sub-system models and memory for simulation"""
        # get simulation time from data client
        self.start_utc = self.data_client.start_utc
        self.end_utc = self.data_client.end_utc

        if not self.start_utc:
            raise ValueError("start_utc is None.")

        if not self.end_utc:
            raise ValueError("end_utc is None.")

        self.state_estimator_model.initialize(
            start_utc=self.start_utc,
            t_start=self.start_time_seconds,
            t_end=self.final_time_seconds,
            t_step=self.step_size_seconds,
            data_spec=data_spec,
            categories_dict=self.data_client.thermostat.get_categories_dict(),
        )
        self.controller_model.update_settings(
            change_points_schedule=self.data_client.thermostat.change_points_schedule,
            change_points_comfort_prefs=self.data_client.thermostat.change_points_comfort_prefs,
            change_points_hvac_mode=self.data_client.thermostat.change_points_hvac_mode,
            init=True,
        )
        self.controller_model.initialize(
            start_utc=self.start_utc,
            t_start=self.start_time_seconds,
            t_end=self.final_time_seconds,
            t_step=self.step_size_seconds,
            data_spec=data_spec,
            categories_dict=self.data_client.thermostat.get_categories_dict(),
        )

        self.building_model.initialize(
            start_utc=self.start_utc,
            t_start=self.start_time_seconds,
            t_end=self.final_time_seconds,
            t_step=self.step_size_seconds,
            data_spec=data_spec,
            categories_dict=self.data_client.thermostat.get_categories_dict(),
        )

        self.allocate_memory()

    def allocate_memory(self):
        """Allocate memory for simulation output"""
        self.output = {}

    def tear_down(self):
        logger.info("Tearing down co-simulation models")
        self.building_model.tear_down()
        self.controller_model.tear_down()

    def run(self, local=True):
        """Main co-simulation loop"""
        logger.info("Initializing co-simulation models")
        self.initialize(data_spec=self.data_client.internal_spec)

        logger.info(
            f"Running co-simulation from {self.start_utc} to {self.end_utc} UTC"
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
            self.state_estimator_model.do_step(
                t_start=_sim_time[i],
                t_step=self.step_size_seconds,
                step_sensor_input=self.building_model.step_output,
            )

            self.controller_model.update_settings(
                change_points_schedule=self.data_client.thermostat.change_points_schedule,
                change_points_comfort_prefs=self.data_client.thermostat.change_points_comfort_prefs,
                change_points_hvac_mode=self.data_client.thermostat.change_points_hvac_mode,
                time_utc=self.data_client.datetime.data.iloc[i][STATES.DATE_TIME],
            )

            self.controller_model.do_step(
                t_start=_sim_time[i],
                t_step=self.step_size_seconds,
                step_thermostat_input=self.data_client.thermostat.data.iloc[i],
                step_sensor_input=self.state_estimator_model.step_output,
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
                STATES.DATE_TIME: self.data_client.datetime.data[STATES.DATE_TIME],
                **self.controller_model.output,
                **self.building_model.output,
            }
        )
        # resample output time steps to output step size frequency
        self.output = self.data_client.resample_to_step_size(
            df=self.output,
            step_size_seconds=self.output_step_size_seconds,
            data_spec=self.data_client.internal_spec,
        )

        self.full_input = self.data_client.get_full_input()

        # create initial mask against index (should be all False)
        _mask = self.output[STATES.DATE_TIME].isnull()
        # only consider data within data periods as output
        for dp_start, dp_end in self.data_client.full_data_periods:
            _mask = _mask | (self.output[STATES.DATE_TIME] >= dp_start) & (
                self.output[STATES.DATE_TIME] < dp_end
            )

        self.output = self.output[_mask]
        self.full_input = self.full_input[_mask]

        # save ouput
        self.data_client.store_output(
            output=self.output,
            sim_name=self.sim_name,
            src_spec=self.data_client.internal_spec,
        )

    def show_plots(self):
        output_analysis = OutputAnalysis(df=self.output_df)
        output_analysis.diagnostic_plot(show=True)
