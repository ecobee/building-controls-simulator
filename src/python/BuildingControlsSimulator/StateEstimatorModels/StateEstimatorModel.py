# created by Tom Stesco tom.s@ecobee.com

from abc import ABC, abstractmethod
from enum import IntEnum
import logging

import attr
import pandas as pd
import numpy as np


@attr.s
class StateEstimatorModel(ABC):
    """ABC for state estimator models"""

    input_states = attr.ib()
    output_states = attr.ib()

    output = attr.ib(factory=dict)
    step_output = attr.ib(factory=dict)
    settings = attr.ib(factory=dict)

    @abstractmethod
    def initialize(self, start_utc, t_start, t_end, t_step, data_spec, categories_dict):
        """Run on first setup and not again."""
        pass

    @abstractmethod
    def do_step(self):
        """Defines sequence of step internals."""
        pass

    @abstractmethod
    def change_settings(self, new_settings):
        """Change persistent internal settings to model."""
        pass

    @abstractmethod
    def get_model_name(self):
        """Defines human readable uniquely identifing name"""
        pass
