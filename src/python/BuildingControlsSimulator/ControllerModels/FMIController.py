# created by Tom Stesco tom.s@ecobee.com

from abc import ABC, abstractmethod
import logging
import os

import attr
import pyfmi

from BuildingControlsSimulator.ControllerModels.ControllerModel import (
    ControllerModel,
)
from BuildingControlsSimulator.ControllerModels.ControllerStatus import CONTROLLERSTATUS


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
        _model_name = os.path.basename(self.fmu_path)
        _model_name = _model_name.replace(".", "_")
        return _model_name
