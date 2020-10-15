# created by Tom Stesco tom.s@ecobee.com
import logging
from pprint import pprint

import attr
import pandas as pd

from BuildingControlsSimulator.DataClients.DataChannel import DataChannel
from BuildingControlsSimulator.DataClients.DataStates import STATES

logger = logging.getLogger(__name__)


@attr.s(kw_only=True)
class EquipmentChannel(DataChannel):

    _placeholder = attr.ib(default=None)