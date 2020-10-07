# created by Tom Stesco tom.s@ecobee.com

from abc import ABC, abstractmethod
from enum import IntEnum
import logging

import attr
import pandas as pd
import numpy as np


@attr.s
class ControlModel(ABC):
    """ABC for control models"""

    input_states = attr.ib()
    output_states = attr.ib()

    output = attr.ib(default={})
    step_output = attr.ib(default={})

    @abstractmethod
    def initialize(self, start_utc, t_start, t_end, ts, categories_dict):
        """Run on first setup and not again."""
        pass

    @abstractmethod
    def do_step(self):
        """Defines sequence of step internals."""
        pass
