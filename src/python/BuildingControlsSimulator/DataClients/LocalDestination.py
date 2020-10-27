# created by Tom Stesco tom.s@ecobee.com

import logging
from abc import ABC, abstractmethod

import attr
import pandas as pd
import numpy as np

from BuildingControlsSimulator.DataClients.DataStates import CHANNELS
from BuildingControlsSimulator.DataClients.DataDestination import (
    DataDestination,
)
from BuildingControlsSimulator.DataClients.DataSpec import (
    convert_spec,
)


logger = logging.getLogger(__name__)


@attr.s(kw_only=True)
class LocalDestination(DataDestination):

    local_cache = attr.ib()

    def put_data(self, df, sim_name, src_spec):
        _df = convert_spec(
            df=df, src_spec=src_spec, dest_spec=self.data_spec, copy=True
        )
        local_cache_file = self.get_local_cache_file(sim_name)
        self.put_local_cache(_df, local_cache_file)
