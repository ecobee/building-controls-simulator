#!/usr/bin/env python
# created by Tom Stesco tom.s@ecobee.com

import os
import subprocess
import shlex
import shutil

import pandas as pd
import numpy as np
from eppy import modeleditor


class Deadband(object):
    """Deadband controller

    Example:
    ```python
    from BuildingControlSimulator.ControlModels.Deadband import Deadband
    controller = Deadband()

    ```

    """
    def __init__(self):
        pass

    def set_point(self, sp):
        pass
        