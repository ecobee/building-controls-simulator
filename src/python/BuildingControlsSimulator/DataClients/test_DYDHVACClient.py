# created by Tom Stesco tom.s@ecobee.com

import logging
import pandas

import pytest

from BuildingControlsSimulator.DataClients.DYDHVACClient import DYDHVACClient

logger = logging.getLogger(__name__)


class TestDYDHVACClient:
    @classmethod
    def setup_class(cls):
        pass

    @classmethod
    def teardown_class(cls):
        """ teardown any state that was previously setup with a call to
        setup_class.
        """
        pass
