# created by Tom Stesco tom.s@ecobee.com

import os
import logging

import pandas as pd
import attr
import numpy as np
from eppy import modeleditor

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s %(levelname)-8s %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
# from BuildingControlSimulator.BuildingModels.BuildingModel import BuildingModel
# from BuildingControlSimulator.BuildingModels.IDFPreprocessor import IDFPreprocessor

@attr.s
class BuildingModel(object):
    """Abstract Base Class for building models
    """

    
    def test_abc(self):
        return 4

