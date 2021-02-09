# created by Tom Stesco tom.s@ecobee.com
import logging
import pytz

from timezonefinder import TimezoneFinder

import attr
import pandas as pd

from BuildingControlsSimulator.DataClients.DataChannel import DataChannel
from BuildingControlsSimulator.DataClients.DataStates import STATES

logger = logging.getLogger(__name__)


@attr.s(kw_only=True)
class DateTimeChannel(DataChannel):

    latitude = attr.ib()
    longitude = attr.ib()
    internal_timezone = attr.ib(default=None)

    @property
    def timezone(self):
        if not self.internal_timezone and (self.latitude and self.longitude):
            # only call _get_timezone once if needed
            self.internal_timezone = DateTimeChannel.get_timezone(
                self.latitude, self.longitude
            )

        return self.internal_timezone

    @staticmethod
    def get_timezone(latitude, longitude):
        """Get pytz timezone object given latitude and longitude."""
        tf = TimezoneFinder()
        return pytz.timezone(
            tf.timezone_at(lng=longitude, lat=latitude)
        )
