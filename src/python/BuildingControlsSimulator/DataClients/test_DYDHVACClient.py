#!/usr/bin/env python
# created by Tom Stesco tom.s@ecobee.com

import logging
import pandas

import pytest

from BuildingControlsSimulator.DataClients.DYDClient import DYDClient
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

    @pytest.mark.run(order=1)
    def test_get_cache(self):
        """
        test that preprocessing produces output file
        """
        dyd = DYDClient()
        logger.info("get data")
        df = dyd.hvac.get_data(
            tstat_ids=["006c7c5d11a0b82b3d91e59b8128307fcb1b40a1"],
            start_utc="2019-01-01",
            end_utc="2019-12-31",
        )
        logger.info("got data")
        assert True
