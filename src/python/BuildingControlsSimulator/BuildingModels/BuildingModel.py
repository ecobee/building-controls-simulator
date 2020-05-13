# created by Tom Stesco tom.s@ecobee.com

import os
import logging

import pandas as pd
import attr
import numpy as np
from eppy import modeleditor


logger = logging.getLogger(__name__)


@attr.s
class BuildingModel(object):
    """Abstract Base Class for building models
    """

    def test_abc(self):
        pass
