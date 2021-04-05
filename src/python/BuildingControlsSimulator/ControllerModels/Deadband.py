# created by Tom Stesco tom.s@ecobee.com
# NOTE: this controller is an over simplified example and does not represent
# anything related to the HVAC control work used or developed at ecobee.

import attr
import pandas as pd
import numpy as np

from BuildingControlsSimulator.ControllerModels.ControllerModel import (
    ControllerModel,
)
from BuildingControlsSimulator.DataClients.DataStates import STATES
from BuildingControlsSimulator.Conversions.Conversions import Conversions


@attr.s
class Deadband(ControllerModel):
    """Deadband controller"""

    deadband = attr.ib(default=1.0)
    step_output = attr.ib(factory=dict)
    step_size_seconds = attr.ib(default=None)
    current_t_idx = attr.ib(default=None)

    output = attr.ib(factory=dict)

    # for reference on how attr defaults wor for mutable types (e.g. list) see:
    # https://www.attrs.org/en/stable/init.html#defaults
    input_states = attr.ib()
    output_states = attr.ib()

    @input_states.default
    def get_input_states(self):
        return [
            STATES.THERMOSTAT_TEMPERATURE_ESTIMATE,
            STATES.TEMPERATURE_STP_COOL,
            STATES.TEMPERATURE_STP_HEAT,
        ]

    @output_states.default
    def get_output_states(self):
        return [
            STATES.TEMPERATURE_CTRL,
            STATES.TEMPERATURE_STP_COOL,
            STATES.TEMPERATURE_STP_HEAT,
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

    def get_model_name(self):
        _model_name = f"Deadband_{self.deadband}"
        _model_name = _model_name.replace(".", "_")
        return _model_name

    def initialize(
        self,
        start_utc,
        t_start,
        t_end,
        t_step,
        data_spec,
        categories_dict,
    ):
        """"""
        self.current_t_idx = 0
        self.step_size_seconds = t_step
        self.allocate_output_memory(
            t_start=t_start,
            t_end=t_end,
            t_step=t_step,
            data_spec=data_spec,
            categories_dict=categories_dict,
        )
        self.init_step_output()

    def allocate_output_memory(
        self, t_start, t_end, t_step, data_spec, categories_dict
    ):
        """preallocate output memory to speed up simulation"""
        # reset output
        self.output = {}

        self.output = {
            STATES.SIMULATION_TIME: np.arange(
                t_start, t_end + t_step, t_step, dtype="int64"
            )
        }
        n_s = len(self.output[STATES.SIMULATION_TIME])

        # add state variables
        for state in self.output_states:
            if data_spec.full.spec[state]["dtype"] == "category":
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
                    data_spec.full.spec[state]["dtype"]
                )
                self.output[state] = np.full(
                    n_s,
                    np_default_value,
                    dtype=np_dtype,
                )

        self.output[STATES.STEP_STATUS] = np.full(n_s, 0, dtype="int8")

    def tear_down(self):
        """tear down FMU"""
        pass

    def init_step_output(self):
        # initialize all off
        self.step_output = {state: 0 for state in self.output_states}

    def calc_t_control(self, step_sensor_input):
        t_ctrl = step_sensor_input[STATES.THERMOSTAT_TEMPERATURE_ESTIMATE]
        return t_ctrl

    def do_step(
        self,
        t_start,
        t_step,
        step_thermostat_input,
        step_sensor_input,
        step_weather_input,
        step_weather_forecast_input,
    ):
        """Simulate controller time step."""
        t_ctrl = self.calc_t_control(step_sensor_input)
        self.step_output[STATES.TEMPERATURE_CTRL] = t_ctrl

        # stop overlap of heating and cooling set points
        self.step_output[STATES.TEMPERATURE_STP_COOL] = max(
            step_thermostat_input[STATES.TEMPERATURE_STP_COOL],
            step_thermostat_input[STATES.TEMPERATURE_STP_HEAT] + self.deadband,
        )
        self.step_output[STATES.TEMPERATURE_STP_HEAT] = min(
            step_thermostat_input[STATES.TEMPERATURE_STP_COOL] - self.deadband,
            step_thermostat_input[STATES.TEMPERATURE_STP_HEAT],
        )

        if t_ctrl < (self.step_output[STATES.TEMPERATURE_STP_HEAT] - self.deadband):
            # turn on heat
            self.step_output[STATES.AUXHEAT1] = self.step_size_seconds
            self.step_output[STATES.FAN_STAGE_ONE] = self.step_size_seconds
            # turn off cool
            self.step_output[STATES.COMPCOOL1] = 0
        elif t_ctrl > (self.step_output[STATES.TEMPERATURE_STP_HEAT] + self.deadband):
            # turn off heat
            self.step_output[STATES.FAN_STAGE_ONE] = 0
            self.step_output[STATES.AUXHEAT1] = 0

        # cooling mode
        if t_ctrl > (self.step_output[STATES.TEMPERATURE_STP_COOL] + self.deadband):
            # turn on cool
            self.step_output[STATES.COMPCOOL1] = self.step_size_seconds
            self.step_output[STATES.FAN_STAGE_ONE] = self.step_size_seconds
            # turn off heat
            self.step_output[STATES.AUXHEAT1] = 0
        elif t_ctrl < (self.step_output[STATES.TEMPERATURE_STP_COOL] - self.deadband):
            # turn off cool
            self.step_output[STATES.FAN_STAGE_ONE] = 0
            self.step_output[STATES.COMPCOOL1] = 0

        self.add_step_to_output(self.step_output)
        self.current_t_idx += 1

        return self.step_output

    def add_step_to_output(self, step_output):
        for k, v in step_output.items():
            self.output[k][self.current_t_idx] = v

    def change_settings(self, new_settings):
        # this model has no settings
        pass
