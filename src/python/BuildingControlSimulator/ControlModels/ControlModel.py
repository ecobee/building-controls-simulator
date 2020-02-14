#!/usr/bin/env python
# created by Tom Stesco tom.s@ecobee.com

import os
import subprocess
import shlex
import shutil
import ABC

import pandas as pd
import numpy as np
from eppy import modeleditor


class ControlModel(object):
    """ABC for control models

    Example:
    ```python
    src.IDFPreprocessor.()

    ```

    """
    def __init__(self):