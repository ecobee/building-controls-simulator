# created by Tom Stesco tom.s@ecobee.com

import os
import subprocess
import shlex
import shutil

import pandas as pd
import attr
import numpy as np
from eppy import modeleditor


from BuildingControlSimulator.BuildingModels.BuildingModel import BuildingModel
from BuildingControlSimulator.BuildingModels.IDFPreprocessor import IDFPreprocessor

@attr.s
class EnergyPlusBuildingModel(BuildingModel):
    """Abstract Base Class for building models


    """
    def __init__(self, idf_path=None, **kwargs):
        """Initialize `IDFPreprocessor` with an IDF file and desired actions"""

        self.idf = IDFPreprocessor(idf_path=idf_path)
        self.idf.add_control()
        self.fmu_path = idf.make_fmu()

    @classmethod
    def from_idf(cls):
        pass

    def test(self):
        return 42


