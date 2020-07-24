# created by Tom Stesco tom.s@ecobee.com

import attr

from BuildingControlsSimulator.ControlModels.ControlModel import ControlModel
from BuildingControlsSimulator.ControlModels.ControlModel import HVAC_modes
import pyfmi


@attr.s(kw_only=True)
class FMIController(ControlModel):
    """Deadband controller

    Example:
    ```python
    from BuildingControlsSimulator.ControlModels.Deadband import Deadband
    ```

    """

    fmu_path = attr.ib()
    HVAC_mode = attr.ib(default=HVAC_modes.UNCONTROLLED)
    stp_heat = attr.ib(default=21.0)
    stp_cool = attr.ib(default=25.0)
    deadband = attr.ib(default=2.0)

    def __attrs_post_init__(self):
        """
        """
        # self.fmu = pyfmi.load_fmu(self.fmu_path)
        pass

    def initialize(self, start_time_seconds, final_time_seconds):
        """
        """
        self.fmu = pyfmi.load_fmu(self.fmu_path)
        self.fmu.initialize(start_time_seconds, final_time_seconds)

    def output_keys(self):
        """
        Data to return in output.
        """
        return ["HVAC_mode", "stp_heat", "stp_cool", "deadband"]

    def do_step(self, t_ctrl):
        """
        Simulate controller time step.
        Before building model step `HVAC_mode` is the HVAC_mode for the step
        """
        self.HVAC_mode = self.next_HVAC_mode(t_ctrl)
        output = [getattr(self, k) for k in self.output_keys()]
        return output

    def next_HVAC_mode(self, t_ctrl):
        """
        Calculate HVAC mode based on current temperature. 
        """
        self.fmu.set("HVACmode", self.HVAC_mode)
        self.fmu.set("Tctrl", t_ctrl)
        self.fmu.set("Thstp", self.stp_heat)
        self.fmu.set("Tcstp", self.stp_cool)
        self.fmu.set("deadBand", self.deadband)

        self.fmu.do_step(
            current_t=0, step_size=300, new_step=True,
        )

        next_HVAC_mode = self.fmu.get("nextHVACmode")[0]

        return next_HVAC_mode
