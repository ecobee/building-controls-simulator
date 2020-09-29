# created by Tom Stesco tom.s@ecobee.com

import os
import logging
import copy

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

from BuildingControlsSimulator.ControlModels.ControlModel import ControlModel
from BuildingControlsSimulator.DataClients.DataClient import DataClient
from BuildingControlsSimulator.OutputAnalysis.OutputAnalysis import (
    OutputAnalysis,
)

logger = logging.getLogger(__name__)


@attr.s(kw_only=True)
class Simulator:
    """Creates list of lazy init simulations with same building model and controller model
    """

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
            member_validator=attr.validators.instance_of(ControlModel),
            iterable_validator=attr.validators.instance_of(list),
        )
    )
    simulations = attr.ib(default=[])
    output_data_dir = attr.ib(
        default=os.path.join(os.environ.get("OUTPUT_DIR"), "data")
    )
    output_plot_dir = attr.ib(
        default=os.path.join(os.environ.get("OUTPUT_DIR"), "plot")
    )

    def __attrs_post_init__(self):
        """Lazy init of all simulations
        """
        # simulation for each permutation: data, building, and controller
        for _idx, _sim_config in self.sim_config.iterrows():

            # the data client is copied once per sim_config so that permutations
            # of building and controller models can reuse data where possible
            dc = copy.deepcopy(self.data_client)
            dc.sim_config = _sim_config
            for b in self.building_models:
                for c in self.controller_models:

                    # lazy init of simulation model
                    # deep copies are used so that models can be in user code
                    # and then be fully initialized lazily per simulation
                    self.simulations.append(
                        Simulation(
                            config=_sim_config,
                            data_client=dc,
                            building_model=copy.deepcopy(b),
                            controller_model=copy.deepcopy(c),
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
