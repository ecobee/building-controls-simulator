# created by Tom Stesco tom.s@ecobee.com

import os
import logging
import copy
from datetime import datetime
import uuid

import pandas as pd
import numpy as np
import attr

from BuildingControlsSimulator.Simulator.Simulation import Simulation
from BuildingControlsSimulator.BuildingModels.BuildingModel import (
    BuildingModel,
)
from BuildingControlsSimulator.BuildingModels.EnergyPlusBuildingModel import (
    EnergyPlusBuildingModel,
)
from BuildingControlsSimulator.BuildingModels.IDFPreprocessor import (
    IDFPreprocessor,
)
from BuildingControlsSimulator.ControllerModels.ControllerModel import (
    ControllerModel,
)
from BuildingControlsSimulator.DataClients.DataClient import DataClient
from BuildingControlsSimulator.ControllerModels.FMIController import (
    FMIController,
)
from BuildingControlsSimulator.ControllerModels.Deadband import Deadband
from BuildingControlsSimulator.StateEstimatorModels.StateEstimatorModel import (
    StateEstimatorModel,
)
from BuildingControlsSimulator.OutputAnalysis.OutputAnalysis import (
    OutputAnalysis,
)

logger = logging.getLogger(__name__)


@attr.s(kw_only=True)
class Simulator:
    """Creates list of lazy init simulations with same building model and controller model"""

    sim_config = attr.ib()
    data_client = attr.ib(validator=attr.validators.instance_of(DataClient))
    building_models = attr.ib(
        validator=attr.validators.deep_iterable(
            member_validator=attr.validators.instance_of(BuildingModel),
            iterable_validator=attr.validators.instance_of(list),
        )
    )
    controller_models = attr.ib(
        validator=attr.validators.deep_iterable(
            member_validator=attr.validators.instance_of(ControllerModel),
            iterable_validator=attr.validators.instance_of(list),
        )
    )
    state_estimator_models = attr.ib(
        validator=attr.validators.deep_iterable(
            member_validator=attr.validators.instance_of(StateEstimatorModel),
            iterable_validator=attr.validators.instance_of(list),
        )
    )

    simulations = attr.ib(factory=list)

    sim_run_identifier = attr.ib()

    @sim_run_identifier.default
    def get_sim_run_identifier(self):
        # use current UTC time as human readable identifier
        # use last 6 chars of hex coded uuid to disambiguate in unlikely case
        # of multiple simulations occuring in same second
        return (
            datetime.utcnow().strftime("%Y_%m_%d_%H_%M_%S")
            + uuid.uuid4().hex[-6:]
        )

    def __attrs_post_init__(self):
        """Lazy init of all simulations"""
        # simulation for each permutation: data, building, and controller
        logger.info(f"Initializing simulation run: {self.sim_run_identifier}")
        for _idx, _sim_config in self.sim_config.iterrows():

            # the data client is copied once per sim_config so that permutations
            # of building and controller models can reuse data where possible
            dc = copy.deepcopy(self.data_client)
            dc.sim_config = _sim_config.to_dict()

            for _b in self.building_models:
                for _c in self.controller_models:
                    for _e in self.state_estimator_models:

                        # lazy init of simulation model
                        # deep copies are used so that models can be in user code
                        # and then be fully initialized lazily per simulation
                        self.simulations.append(
                            Simulation(
                                config=_sim_config,
                                data_client=dc,
                                building_model=copy.deepcopy(_b),
                                controller_model=copy.deepcopy(_c),
                                state_estimator_model=copy.deepcopy(_e),
                                sim_run_identifier=self.sim_run_identifier,
                            )
                        )

    def simulate(self, local=True, preprocess_check=False):
        """Run all simulations locally or in cloud.
        :param local: run simulations locally
        """
        if local:
            for sim in self.simulations:
                # weather data is required during model creation
                sim.data_client.get_data()
                sim.create_models(preprocess_check=preprocess_check)
                sim.run(local=True)
