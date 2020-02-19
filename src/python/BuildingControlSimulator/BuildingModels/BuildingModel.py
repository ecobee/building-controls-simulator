# created by Tom Stesco tom.s@ecobee.com

import os

import pandas as pd
import attr
import numpy as np
from eppy import modeleditor


# from BuildingControlSimulator.BuildingModels.BuildingModel import BuildingModel
# from BuildingControlSimulator.BuildingModels.IDFPreprocessor import IDFPreprocessor

@attr.s
class BuildingModel(object):
    """Abstract Base Class for building models
    """

    
    def test_abc(self):
        return 4

