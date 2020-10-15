# created by Tom Stesco tom.s@ecobee.com
import logging
from pprint import pprint
import pytz

from tzwhere import tzwhere
import attr
import pandas as pd

from BuildingControlsSimulator.DataClients.DataChannel import DataChannel
from BuildingControlsSimulator.DataClients.DataStates import STATES

logger = logging.getLogger(__name__)


@attr.s(kw_only=True)
class DateTimeChannel(DataChannel):

    latitude = attr.ib()
    longitude = attr.ib()
    timezone = attr.ib(default=None)

    def __attrs_post_init__(self):
        self.timezone = self.get_timezone()

    def get_timezone(self):
        """Get pytz timezone object given latitude and longitude."""
        tzw = tzwhere.tzwhere(forceTZ=True)
        return pytz.timezone(
            tzw.tzNameAt(
                latitude=self.latitude,
                longitude=self.longitude,
                forceTZ=True,
            )
        )