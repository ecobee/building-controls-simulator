# created by Tom Stesco tom.s@ecobee.com

import os
import logging

import pandas as pd
import numpy as np
import attr

from BuildingControlsSimulator.Simulator.Simulation import Simulation
from BuildingControlsSimulator.BuildingModels.BuildingModel import (
    BuildingModel,
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
        for identifier, sim_config in self.sim_config.iterrows():
            breakpoint()
            for b in self.building_models:

                for c in self.controller_models:

                    # lazy init of simulation model
                    self.simulations.append(
                        Simulation(
                            config=sim_config,
                            data_client=self.data_client[identifier],
                            building_model=b,
                            controller_model=c,
                        )
                    )

    def simulate(self, local=True):
        """Run all simulations locally or in cloud.


        :param local:
        """
        if local:
            for s in self.simulations:
                s.run(local=True)

