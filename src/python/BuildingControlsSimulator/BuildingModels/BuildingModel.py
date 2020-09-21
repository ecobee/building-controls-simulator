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
    """Abstract Base Class for building models
    """

    input_states = attr.ib()
    output_states = attr.ib()

    @abstractmethod
    def initialize(self, t_start, t_end, ts):
        pass

    @abstractmethod
    def do_step(self):
        """
        Defines sequence of step internals.
        """
        pass
