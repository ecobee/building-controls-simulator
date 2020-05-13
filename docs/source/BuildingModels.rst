BuildingModels
=======================
Thermodynamic models of buildings.



.. currentmodule:: BuildingControlsSimulator.BuildingModels.BuildingModel

BuildingModel
-----------------------

.. note::
    Abstract Base Class for all building models. This enforces a standard API to 
    allow compatability of different building model implementations.

.. autosummary::
    :toctree: generated
    :nosignatures:
    
    BuildingModel
    BuildingModel.test_abc

.. currentmodule:: BuildingControlsSimulator.BuildingModels.EnergyPlusBuildingModel

EnergyPlusBuildingModel
-----------------------

.. note::
    Creates and manages EnergyPlus building models.

.. autosummary::
    :toctree: generated
    :nosignatures:

    EnergyPlusBuildingModel
    EnergyPlusBuildingModel.create_model_fmu
    EnergyPlusBuildingModel.occupied_zones
    EnergyPlusBuildingModel.actuate_HVAC_equipment


.. currentmodule:: BuildingControlsSimulator.BuildingModels.IDFPreprocessor

IDFPreprocessor
-----------------------

.. note::
   Handles preprocessing of EnergyPlus IDFs (Input Data Files).

.. autosummary::
    :toctree: generated
    :nosignatures:

    IDFPreprocessor
    IDFPreprocessor.preprocess