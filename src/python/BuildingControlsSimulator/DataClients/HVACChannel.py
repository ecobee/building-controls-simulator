# created by Tom Stesco tom.s@ecobee.com

import logging

import attr
import pandas as pd
import numpy as np

from BuildingControlsSimulator.DataClients.DataChannel import DataChannel

logger = logging.getLogger(__name__)


@attr.s(kw_only=True)
class HVACChannel(DataChannel):

    extra = attr.ib(default=None)
