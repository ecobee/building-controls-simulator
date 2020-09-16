# created by Tom Stesco tom.s@ecobee.com

import attr
import pandas as pd
import numpy as np

from BuildingControlsSimulator.ControlModels.ControlModel import ControlModel
from BuildingControlsSimulator.ControlModels.ControlModel import HVAC_modes


@attr.s
class Deadband(ControlModel):
    """Deadband controller

    Example:
    ```python
    from BuildingControlsSimulator.ControlModels.Deadband import Deadband
    ```

    """

    deadband = attr.ib(default=1.0)
    input_spec = attr.ib(
        default={
            "tstat_temperature": {
                "input_name": "tstat_temperature",
                "dtype": "float32",
            },
            "cool_set_point": {
                "input_name": "cool_set_point",
                "dtype": "float32",
            },
            "heat_set_point": {
                "input_name": "heat_set_point",
                "dtype": "float32",
            },
        }
    )

    output_spec = attr.ib(
        default={
            "heat_stage_one": {
                "output_name": "heat_stage_one",
                "dtype": "bool",
            },
            "heat_stage_two": {
                "output_name": "heat_stage_two",
                "dtype": "bool",
            },
            "heat_stage_three": {
                "output_name": "heat_stage_three",
                "dtype": "bool",
            },
            "compressor_cool_stage_one": {
                "output_name": "compressor_cool_stage_one",
                "dtype": "bool",
            },
            "compressor_cool_stage_two": {
                "output_name": "compressor_cool_stage_two",
                "dtype": "bool",
            },
            "compressor_heat_stage_one": {
                "output_name": "compressor_heat_stage_one",
                "dtype": "bool",
            },
            "compressor_heat_stage_two": {
                "output_name": "compressor_heat_stage_two",
                "dtype": "bool",
            },
            "fan_stage_one": {
                "output_name": "fan_stage_one",
                "dtype": "bool",
            },
            "fan_stage_two": {
                "output_name": "fan_stage_two",
                "dtype": "bool",
            },
            "fan_stage_three": {
                "output_name": "fan_stage_three",
                "dtype": "bool",
            },
        }
    )
    step_output = attr.ib(
        default={
            "heat_stage_one": False,
            "heat_stage_two": False,
            "heat_stage_three": False,
            "compressor_cool_stage_one": False,
            "compressor_cool_stage_two": False,
            "compressor_cool_stage_one": False,
            "compressor_cool_stage_three": False,
            "fan_stage_one": False,
            "fan_stage_two": False,
            "fan_stage_three": False,
        }
    )

    output = attr.ib(default={})
    current_t_idx = attr.ib(default=0)

    def initialize(self, t_start, t_end, ts):
        """
        """
        self.output["time"] = np.arange(t_start, t_end, ts, dtype="int64")
        n_s = len(self.output["time"])
        self.output = {}

        # add fmu state variables
        for k, v, in self.output_spec.items():
            if v["dtype"] == "bool":
                self.output[k] = np.full(n_s, False, dtype="bool")
            elif v["dtype"] == "float32":
                self.output[k] = np.full(n_s, -999, dtype="float32")
            else:
                raise ValueError(
                    "Unsupported output_map dtype: {}".format(v["dtype"])
                )

        self.output["status"] = np.full(n_s, False, dtype="bool")

    def get_t_ctrl(self, tstat_temperature):
        """
        """
        return np.mean(tstat_temperature)

    def do_step(self, step_input):
        """
        Simulate controller time step.
        Before building model step `HVAC_mode` is the HVAC_mode for the step
        """
        t_ctrl = self.get_t_ctrl(step_input["tstat_temperature"])

        if (
            t_ctrl < (step_input["heat_set_point"] - self.deadband)
            and not self.step_output["heat_stage_one"]
        ):
            # turn on heat
            self.step_output["heat_stage_one"] = True
            self.step_output["fan_stage_one"] = True

        if (
            t_ctrl > (step_input["heat_set_point"] + self.deadband)
            and self.step_output["heat_stage_one"]
        ):
            # turn off heat
            self.step_output["heat_stage_one"] = False
            self.step_output["fan_stage_one"] = False

        if (
            t_ctrl > (step_input["cool_set_point"] + self.deadband)
            and not self.step_output["compressor_cool_stage_one"]
        ):
            # turn on cool
            self.step_output["compressor_cool_stage_one"] = True
            self.step_output["fan_stage_one"] = True

        if (
            t_ctrl < (step_input["cool_set_point"] - self.deadband)
            and self.step_output["compressor_cool_stage_one"]
        ):
            # turn off cool
            self.step_output["compressor_cool_stage_one"] = False
            self.step_output["fan_stage_one"] = False

        self.add_step_to_output(self.step_output)

        return self.step_output

    def add_step_to_output(self, step_output):
        for k, v in step_output.items():
            self.output["k"][self.current_t_idx] = v

        self.current_t_idx += 1
