from BuildingControlSimulator.BuildingModels.BuildingModel import BuildingModel
from BuildingControlSimulator.BuildingModels.IDFPreprocessor import IDFPreprocessor

class EnergyPlusBuildingModel(BuildingModel):
    """Abstract Base Class for building models


    """
    def __init__(self, idf_path=None, **kwargs):
        """Initialize `IDFPreprocessor` with an IDF file and desired actions"""

        self.idf = IDFPreprocessor(idf_path=idf_path)
        self.idf.add_control()
        self.fmu_path = idf.make_fmu()


    def test(self):
        return 42


