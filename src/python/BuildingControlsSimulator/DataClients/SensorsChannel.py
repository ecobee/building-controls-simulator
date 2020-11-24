# created by Tom Stesco tom.s@ecobee.com

import logging

import attr
import pandas as pd
import numpy as np

from BuildingControlsSimulator.DataClients.DataChannel import DataChannel
from BuildingControlsSimulator.DataClients.DataStates import STATES

logger = logging.getLogger(__name__)


@attr.s(kw_only=True)
class SensorsChannel(DataChannel):
    def __attrs_post_init__(self):
        # validate sensor data
        if all(self.data[STATES.THERMOSTAT_MOTION].isnull()):
            raise NotImplementedError(
                "Support for devices without thermostat motion sensor."
            )

        self.drop_unused_room_sensors()

    def drop_unused_room_sensors(self):
        """null room sensors temperature and motion data can safely be dropped"""
        drop_columns = []
        for _col in self.data.columns:
            # check for room sensor states
            if str(_col).startswith("STATES.RS"):
                if self.data[_col].isnull().all():
                    drop_columns.append(_col)

        self.data = self.data.drop(axis=1, columns=drop_columns)
