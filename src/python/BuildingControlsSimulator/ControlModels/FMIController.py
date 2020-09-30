# created by Tom Stesco tom.s@ecobee.com

from abc import ABC, abstractmethod
import logging

import attr
import pyfmi

from BuildingControlsSimulator.ControlModels.ControlModel import ControlModel


@attr.s(kw_only=True)
class FMIController(ControlModel):
    """Deadband controller

    Example:
    ```python
    from BuildingControlsSimulator.ControlModels.Deadband import Deadband
    ```

    """

    fmu_path = attr.ib()

    current_t_idx = attr.ib(default=None)
    step_size_seconds = attr.ib()
