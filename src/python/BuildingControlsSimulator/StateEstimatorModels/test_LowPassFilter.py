# created by Tom Stesco tom.s@ecobee.com

import logging

import pytest
import pandas as pd
import numpy as np

from BuildingControlsSimulator.DataClients.DataStates import STATES
from BuildingControlsSimulator.DataClients.DataSpec import Internal
from BuildingControlsSimulator.StateEstimatorModels.LowPassFilter import LowPassFilter

logger = logging.getLogger(__name__)


class TestLowPassFilter:
    @classmethod
    def setup_class(cls):
        # initialize with data to avoid pulling multiple times
        cls.step_size_seconds = 300

    @classmethod
    def teardown_class(cls):
        """teardown any state that was previously setup with a call to
        setup_class.
        """
        pass

    def test_low_pass_filter(self):
        # test HVAC data returns dict of non-empty pd.DataFrame
        state_estimator_model = LowPassFilter(
            alpha_temperature=0.75, alpha_humidity=0.75
        )

        test_temperature = np.arange(-40, 60, 0.05)
        test_humidity = np.linspace(0, 100, len(test_temperature))
        test_motion = np.full(len(test_temperature), False)
        test_sim_time = np.arange(
            0,
            len(test_temperature) * self.step_size_seconds,
            self.step_size_seconds,
            dtype="int64",
        )

        test_sensor_data = pd.DataFrame.from_dict(
            {
                STATES.THERMOSTAT_TEMPERATURE: test_temperature,
                STATES.THERMOSTAT_HUMIDITY: test_humidity,
                STATES.THERMOSTAT_MOTION: test_humidity,
            }
        )

        state_estimator_model.initialize(
            start_utc=pd.Timestamp("now"),
            t_start=0,
            t_end=len(test_temperature) * self.step_size_seconds,
            t_step=self.step_size_seconds,
            data_spec=Internal(),
            categories_dict={},
        )

        for i in range(0, len(test_sim_time)):
            state_estimator_model.do_step(
                t_start=test_sim_time[i],
                t_step=self.step_size_seconds,
                step_sensor_input=test_sensor_data.iloc[i],
            )

        test_output = pd.DataFrame.from_dict(state_estimator_model.output)
        test_output = test_output.drop(axis="rows", index=len(test_sim_time))

        assert (
            pytest.approx(9.95837688446045)
            == test_output[STATES.THERMOSTAT_TEMPERATURE_ESTIMATE].mean()
        )
        assert (
            test_sensor_data[STATES.THERMOSTAT_TEMPERATURE].mean()
            > test_output[STATES.THERMOSTAT_TEMPERATURE_ESTIMATE].mean()
        )
        assert (
            pytest.approx(49.98334503173828)
            == test_output[STATES.THERMOSTAT_HUMIDITY_ESTIMATE].mean()
        )
        assert (
            test_sensor_data[STATES.THERMOSTAT_HUMIDITY].mean()
            > test_output[STATES.THERMOSTAT_HUMIDITY_ESTIMATE].mean()
        )
