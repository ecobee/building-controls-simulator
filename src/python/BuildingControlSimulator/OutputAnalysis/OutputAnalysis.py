# created by Tom Stesco tom.s@ecobee.com

import os
import subprocess
import shlex
import shutil

import pandas as pd
import numpy as np
from eppy import modeleditor
import attr
import pyfmi

from BuildingControlSimulator.ControlModels import ControlModel
from BuildingControlSimulator.BuildingModels import IDFPreprocessor

@attr.s
class OutputAnalysis(object):
    """Deadband controller

    Example:
    ```python
    from BuildingControlSimulator.ControlModels.Deadband import Deadband
    controller = Deadband()

    ```

    """
    deadband = attr.ib(kw_only=True)
    bm = attr.ib(kw_only=True)
    stp_heat = attr.ib(default=21.)
    stp_cool = attr.ib(default=25.)
    # HVAC_mode = attr.ib(kw_only=True)
    HVAC_mode = attr.ib(default=HVAC_modes.UNCONTROLLED)
    T_heat_off = attr.ib(default=-60.0)
    T_heat_on = attr.ib(default=99.0)
    T_cool_off = attr.ib(default=99.0)
    T_cool_on = attr.ib(default=-60.0)

    @classmethod
    def from_idf_deadband(cls, building_model, idf, controller):
        pass

    @classmethod
    def from_simulator(cls, simulator):
        pass


        