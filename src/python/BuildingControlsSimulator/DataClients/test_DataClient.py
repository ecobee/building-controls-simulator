# created by Tom Stesco tom.s@ecobee.com
import logging
import os
import copy

import pytest
import pandas as pd
import numpy as np

from BuildingControlsSimulator.Simulator.Config import Config
from BuildingControlsSimulator.DataClients.DataClient import DataClient
from BuildingControlsSimulator.DataClients.LocalSource import (
    LocalSource,
)
from BuildingControlsSimulator.DataClients.LocalDestination import (
    LocalDestination,
)
from BuildingControlsSimulator.DataClients.DataSpec import EnergyPlusWeather
from BuildingControlsSimulator.DataClients.DataStates import STATES
from BuildingControlsSimulator.DataClients.DataSpec import (
    Internal,
    DonateYourDataSpec,
    convert_spec,
)

logger = logging.getLogger(__name__)


class TestDataClient:
    @classmethod
    def setup_class(cls):
        # initialize with data to avoid pulling multiple times

        cls.sim_config = Config.make_sim_config(
            identifier=[
                "DYD_dummy_data",  # test file
            ],
            latitude=33.481136,
            longitude=-112.078232,
            start_utc=[
                "2018-01-01 00:00:00",
            ],
            end_utc=[
                "2018-12-31 23:55:00",
            ],
            min_sim_period="3D",
            min_chunk_period="30D",
            sim_step_size_seconds=300,
            output_step_size_seconds=300,
        )

        cls.data_client = DataClient(
            source=LocalSource(
                local_cache=os.environ.get("LOCAL_CACHE_DIR"),
                data_spec=DonateYourDataSpec(),
            ),
            destination=LocalDestination(
                local_cache=os.environ.get("LOCAL_CACHE_DIR"),
                data_spec=DonateYourDataSpec(),
            ),
        )
        cls.data_client.sim_config = cls.sim_config.iloc[0]

        cls.data_client.get_data()
        # pass

    @classmethod
    def teardown_class(cls):
        """teardown any state that was previously setup with a call to
        setup_class.
        """
        pass

    def test_dummy_data_generator(self):
        _sim_config = Config.make_sim_config(
            identifier=[
                "generated_dummy_data",  # test file
            ],
            latitude=33.481136,
            longitude=-112.078232,
            start_utc=[
                "2018-01-01 00:00:00",
            ],
            end_utc=[
                "2018-12-31 23:55:00",
            ],
            min_sim_period="3D",
            min_chunk_period="30D",
            sim_step_size_seconds=300,
            output_step_size_seconds=300,
        )
        DataClient.generate_dummy_data(sim_config=_sim_config, spec=Internal())
        pass

    def test_upresample_to_step_size(self):
        df = self.data_client.get_full_input()
        _col = STATES.AUXHEAT1
        _sequence = np.array(
            [
                0,
                150,
                150,
                150,
                150,
                30,
                270,
                30,
                270,
                0,
                300,
                300,
                240,
                0,
                150,
                300,
                150,
            ]
        )
        df.loc[0 : len(_sequence) - 1, _col] = _sequence

        res_df = DataClient.upsample_to_step_size(
            df, step_size_seconds=60, data_spec=self.data_client.internal_spec
        )
        # check sum
        res_rt = np.sum(_sequence)
        res_sum_rt = np.sum(res_df.loc[0 : (len(_sequence) - 1) * 5, _col].values)
        assert res_rt == res_sum_rt

        # check exact sequence
        assert all(
            res_df.loc[0 : (len(_sequence) - 1) * 5, _col].values
            == np.array(
                [
                    0,
                    0,
                    0,
                    30,
                    60,
                    60,
                    60,
                    60,
                    30,
                    0,
                    0,
                    0,
                    0,
                    30,
                    60,
                    60,
                    60,
                    60,
                    30,
                    0,
                    0,
                    0,
                    0,
                    0,
                    0,
                    30,
                    60,
                    60,
                    60,
                    60,
                    30,
                    0,
                    0,
                    0,
                    0,
                    30,
                    60,
                    60,
                    60,
                    60,
                    30,
                    0,
                    0,
                    0,
                    0,
                    0,
                    60,
                    60,
                    60,
                    60,
                    60,
                    60,
                    60,
                    60,
                    60,
                    60,
                    60,
                    60,
                    60,
                    60,
                    0,
                    0,
                    0,
                    0,
                    0,
                    0,
                    0,
                    0,
                    30,
                    60,
                    60,
                    60,
                    60,
                    60,
                    60,
                    60,
                    0,
                    0,
                    30,
                    60,
                    60,
                ]
            )
        )
