# created by Tom Stesco tom.s@ecobee.com

from abc import ABC, abstractmethod
from enum import IntEnum
import logging

import attr
import pandas as pd
import numpy as np


@attr.s
class ControlModel(ABC):
    """ABC for control models  
    """

    input_states = attr.ib()
    output_states = attr.ib()

    @abstractmethod
    def initialize(self, t_start, t_end, ts):
        """
        Run on first setup and not again.
        """
        pass

    @abstractmethod
    def do_step(self):
        """
        Defines sequence of step internals.
        """
        pass

    # @property
    # def input_keys(self):
    #     return [v["input_name"] for k, v in self.input_spec.items()]

    # @property
    # def output_keys(self):
    #     return [v["output_name"] for k, v in self.output_spec.items()]

    # def get_step_input(self, step_input):
    #     return {
    #         v["input_name"]: step_input[k] for k, v in self.input_spec.items()
    #     }

    # def get_step_output(self, step_output):
    #     return {
    #         v["output_name"]: step_output[k]
    #         for k, v in self.output_spec.items()
    #     }

    # FMU_control_cooling_stp_name = attr.ib(kw_only=True)
    # FMU_control_heating_stp_name = attr.ib(kw_only=True)
    # FMU_control_type_name = attr.ib(kw_only=True)
    # def __init__(self,
    #     FMU_control_heating_stp_name,
    #     FMU_control_cooling_stp_name,
    #     FMU_control_type_name):
    # """
    # """
    #     self.allowed_keys = [
    #         "FMU_control_cooling_stp_name",
    #         "FMU_control_heating_stp_name",
    #         "FMU_control_type_name"
    #     ]
    #     for key, value in kwargs.items():
    #         if key in allowed_keys:
    #             setattr(self, key, value)
