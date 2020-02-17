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
    def __init__(self, deadband, building_model=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.deadband = deadband

    def from_idf(self, building_model):
        pass


        