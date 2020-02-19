# created by Tom Stesco tom.s@ecobee.com

import os
from enum import Enum
import subprocess
import shlex
import shutil

import pandas as pd
import numpy as np
from eppy import modeleditor
import attr
import pyfmi

from BuildingControlSimulator.ControlModels.ControlModel import ControlModel
from BuildingControlSimulator.ControlModels.ControlModel import HVAC_modes
from BuildingControlSimulator.BuildingModels import IDFPreprocessor


@attr.s
class Deadband(ControlModel):
    """Deadband controller

    Example:
    ```python
    from BuildingControlSimulator.ControlModels.Deadband import Deadband


    ```

    """

    # bm = attr.ib(kw_only=True)
    # HVAC_mode = attr.ib(kw_only=True)
    HVAC_mode = attr.ib(default=HVAC_modes.UNCONTROLLED)
    stp_heat = attr.ib(default=21.)
    stp_cool = attr.ib(default=25.)
    deadband = attr.ib(default=2.)

    def output_keys(self):
        """
        """
        return [
            "HVAC_mode",
            "stp_heat",
            "stp_cool",
            "deadband"
        ]

    def do_step(self, t_ctrl):
        """
        before building model step `HVAC_mode` is the HVAC_mode for the step
        """
        self.HVAC_mode = self.next_HVAC_mode(t_ctrl)
        output = [getattr(self, k) for k in self.output_keys()] 
        return output

    def next_HVAC_mode(self, t_ctrl):
        """ 
        """

        next_HVAC_mode = self.HVAC_mode
        if (
            t_ctrl < (self.stp_heat - self.deadband)
            and self.HVAC_mode != HVAC_modes.SINGLE_HEATING_SETPOINT
        ):
            # turn on heat
            next_HVAC_mode = HVAC_modes.SINGLE_HEATING_SETPOINT

        if (
            t_ctrl > (self.stp_heat + self.deadband)
            and self.HVAC_mode == HVAC_modes.SINGLE_HEATING_SETPOINT
        ):
            # turn off heat
            next_HVAC_mode = HVAC_modes.UNCONTROLLED

        if (
            t_ctrl > (self.stp_cool + self.deadband)
            and self.HVAC_mode != HVAC_modes.SINGLE_COOLING_SETPOINT
        ):
            # turn on cool
            next_HVAC_mode = HVAC_modes.SINGLE_COOLING_SETPOINT

        if (
            t_ctrl < (self.stp_cool - self.deadband)
            and self.HVAC_mode == HVAC_modes.SINGLE_COOLING_SETPOINT
        ):
            # turn off cool
            next_HVAC_mode = HVAC_modes.UNCONTROLLED

        return next_HVAC_mode

    


