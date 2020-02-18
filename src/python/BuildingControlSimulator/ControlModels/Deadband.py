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

    bm = attr.ib(kw_only=True)
    # HVAC_mode = attr.ib(kw_only=True)
    HVAC_mode = attr.ib(default=HVAC_modes.UNCONTROLLED)
    stp_heat = attr.ib(default=21.)
    stp_cool = attr.ib(default=25.)
    deadband = attr.ib(default=2.)
    T_heat_off = attr.ib(default=-60.0)
    T_heat_on = attr.ib(default=99.0)
    T_cool_off = attr.ib(default=99.0)
    T_cool_on = attr.ib(default=-60.0)

    @classmethod
    def from_idf(cls, building_model, idf):
        return cls(
            bm=building_model,
            FMU_control_heating_stp_name=idf.FMU_control_heating_stp_name,
            FMU_control_cooling_stp_name=idf.FMU_control_cooling_stp_name,
            FMU_control_type_name=idf.FMU_control_type_name
        )

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
        """
        next_HVAC_mode = self.next_HVAC_mode(t_ctrl)
        self.actuate_HVAC_mode(next_HVAC_mode)
        self.HVAC_mode = next_HVAC_mode
        return [getattr(self, k) for k in self.output_keys()]

    def next_HVAC_mode(self, t_ctrl):
        """ 
        """

        _HVAC_mode = self.HVAC_mode
        if (
            t_ctrl < (self.stp_heat - self.deadband)
            and self.HVAC_mode != HVAC_modes.SINGLE_HEATING_SETPOINT
        ):
            # turn on heat
            _HVAC_mode = HVAC_modes.SINGLE_HEATING_SETPOINT

        if (
            t_ctrl > (self.stp_heat + self.deadband)
            and self.HVAC_mode == HVAC_modes.SINGLE_HEATING_SETPOINT
        ):
            # turn off heat
            _HVAC_mode = HVAC_modes.UNCONTROLLED

        if (
            t_ctrl > (self.stp_cool + self.deadband)
            and self.HVAC_mode != HVAC_modes.SINGLE_COOLING_SETPOINT
        ):
            # turn on cool
            _HVAC_mode = HVAC_modes.SINGLE_COOLING_SETPOINT

        # if t_ctrl < (self.stp_cool - self.deadband) and t_ctrl > (
        #     self.stp_heat - self.deadband
        # ):
        #     _HVAC_mode = HVAC_modes.UNCONTROLLED

        if (
            t_ctrl < (self.stp_cool - self.deadband)
            and self.HVAC_mode == HVAC_modes.SINGLE_COOLING_SETPOINT
        ):
            # turn off cool
            _HVAC_mode = HVAC_modes.UNCONTROLLED

        return _HVAC_mode

    def actuate_HVAC_mode(self, next_HVAC_mode):
        """
        """
        if self.HVAC_mode != next_HVAC_mode:
            if next_HVAC_mode == HVAC_modes.SINGLE_HEATING_SETPOINT:
                self.bm.set(self.FMU_control_type_name, int(next_HVAC_mode))
                self.bm.set(self.FMU_control_heating_stp_name, self.T_heat_on)
                self.bm.set(self.FMU_control_cooling_stp_name, self.T_cool_off)
            elif next_HVAC_mode == HVAC_modes.SINGLE_COOLING_SETPOINT:
                self.bm.set(self.FMU_control_type_name, int(next_HVAC_mode))
                self.bm.set(self.FMU_control_heating_stp_name, self.T_heat_off)
                self.bm.set(self.FMU_control_cooling_stp_name, self.T_cool_on)

            elif next_HVAC_mode == HVAC_modes.UNCONTROLLED:
                self.bm.set(self.FMU_control_type_name, int(next_HVAC_mode))
                self.bm.set(self.FMU_control_heating_stp_name, self.T_heat_off)
                self.bm.set(self.FMU_control_cooling_stp_name, self.T_cool_off)


