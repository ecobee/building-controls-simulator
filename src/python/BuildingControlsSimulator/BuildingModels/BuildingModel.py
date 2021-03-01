# created by Tom Stesco tom.s@ecobee.com

import os
import logging
from abc import ABC, abstractmethod


import pandas as pd
import attr
import numpy as np
from eppy import modeleditor


logger = logging.getLogger(__name__)


@attr.s
class BuildingModel(ABC):
    """Abstract Base Class for building models"""

    input_states = attr.ib()
    output_states = attr.ib()
    step_size_seconds = attr.ib()

    status = attr.ib(default=0)
    log_level = attr.ib(default=0)

    @abstractmethod
    def initialize(self, start_utc, t_start, t_end, t_step, data_spec, categories_dict):
        pass

    @abstractmethod
    def do_step(self):
        """
        Defines sequence of step internals.
        """
        pass

    @abstractmethod
    def get_model_name(self):
        """Defines human readable uniquely identifing name"""
        pass
