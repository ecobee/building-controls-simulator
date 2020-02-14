#!/usr/bin/env python
# created by Tom Stesco tom.s@ecobee.com

import os
import subprocess
import shlex
import shutil

import pandas as pd
import numpy as np

from eppy import modeleditor
import pyfmi

from BuildingControlSimulator.BuildingModels.IDFPreprocessor import IDFPreprocessor
from BuildingControlSimulator.ControlModels.Deadband import Deadband

class Simulator(object):
    """Converts IDFs (Input Data Files) for EnergyPlus into working IDFs.

    Example:
    ```python
    src.IDFPreprocessor.()

    ```

    """
    def __init__(self):
        self.control_model = ""
        self.building_model = ""
        self.output_dir = os.path.join(os.environ["PACKAGE_DIR"], "data")

        