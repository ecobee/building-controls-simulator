# created by Tom Stesco tom.s@ecobee.com

import subprocess
import os
import shutil
import logging

import pytest
import pandas as pd
import numpy as np

from BuildingControlsSimulator.Metrics.Metric import Metric

logger = logging.getLogger(__name__)


class TestMetric:
    @classmethod
    def setup_class(cls):
        pass

    @classmethod
    def teardown_class(cls):
        """teardown any state that was previously setup with a call to
        setup_class.
        """
        pass

    def get_conseq_dt(self):
        return pd.to_datetime(
            [
                "2019-01-12T09:05:00.000000000",
                "2019-01-12T09:10:00.000000000",
                "2019-01-12T09:15:00.000000000",
                "2019-01-12T09:20:00.000000000",
                "2019-01-12T09:25:00.000000000",
                "2019-01-12T09:30:00.000000000",
                "2019-01-12T09:35:00.000000000",
                "2019-01-12T09:40:00.000000000",
                "2019-01-12T09:45:00.000000000",
                "2019-01-12T09:50:00.000000000",
            ],
            utc=True,
        )

    def test_HVAC_cycles_conseq(self):
        m = Metric()
        cycles1 = m.HVAC_cycles(
            pd.DataFrame.from_dict(
                {
                    "datetime": self.get_conseq_dt()[0:8],
                    "compCool1": [0, 0, 75, 300, 300, 25, 0, 0],
                }
            )
        )

        cycles2 = m.HVAC_cycles(
            pd.DataFrame.from_dict(
                {
                    "datetime": self.get_conseq_dt()[0:8],
                    "compCool1": [0, 300, 0, 75, 300, 100, 200, 115],
                }
            )
        )

        cycles3 = m.HVAC_cycles(
            pd.DataFrame.from_dict(
                {
                    "datetime": self.get_conseq_dt()[0:10],
                    "compCool1": [
                        300,
                        75,
                        225,
                        300,
                        300,
                        300,
                        100,
                        200,
                        115,
                        0,
                    ],
                }
            )
        )

        cycles4 = m.HVAC_cycles(
            pd.DataFrame.from_dict(
                {
                    "datetime": self.get_conseq_dt()[0:6],
                    "compCool1": [
                        300,
                        0,
                        300,
                        0,
                        300,
                        0,
                    ],
                }
            )
        )
        print("ok")
