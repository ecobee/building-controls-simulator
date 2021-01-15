# created by Tom Stesco tom.s@ecobee.com

from abc import ABC, abstractmethod
import logging
import os

import attr
import pyfmi

from BuildingControlsSimulator.ControllerModels.ControllerModel import (
    ControllerModel,
)


@attr.s(kw_only=True)
class FMIController(ControllerModel):
    """Deadband controller

    Example:
    ```python
    from BuildingControlsSimulator.ControllerModels.Deadband import Deadband
    ```

    """

    fmu_path = attr.ib()

    current_t_idx = attr.ib(default=None)
    step_size_seconds = attr.ib()

    def get_model_name(self):
        fmu_name = os.path.basename(self.fmu_path)
        return f"FMU_{fmu_name}"
