#!/usr/bin/env python
# created by Tom Stesco tom.s@ecobee.com

import subprocess
import os
import shutil
import logging
import pytz

import pytest
import pyfmi

from BuildingControlsSimulator.Simulator.Config import Config
from BuildingControlsSimulator.BuildingModels.IDFPreprocessor import (
    IDFPreprocessor,
)
from BuildingControlsSimulator.BuildingModels.EnergyPlusBuildingModel import (
    EnergyPlusBuildingModel,
)


logger = logging.getLogger(__name__)


class TestIDFPreprocessor:
    @classmethod
    def setup_class(cls):
        # basic IDF file found in all EnergyPlus installations
        cls.dummy_idf_name = "Furnace.idf"
        cls.dummy_weather_name = "USA_IL_Chicago-OHare.Intl.AP.725300_TMY3.epw"

        # make test/ dirs
        EnergyPlusBuildingModel.make_directories()

        cls.dummy_idf_path = os.path.join(
            os.environ.get("IDF_DIR"), cls.dummy_idf_name
        )

        cls.dummy_weather_file = os.path.join(
            os.environ.get("WEATHER_DIR"), cls.dummy_weather_name
        )

        # if dummy files don't exist copy them from E+ installations
        if not os.path.isfile(cls.dummy_idf_path):
            _fpath = os.path.join(
                os.environ.get("EPLUS_DIR"), "ExampleFiles", cls.dummy_idf_name
            )
            shutil.copyfile(_fpath, cls.dummy_idf_path)

        if not os.path.isfile(cls.dummy_weather_file):
            _fpath = os.path.join(
                os.environ.get("EPLUS_DIR"),
                "WeatherData",
                cls.dummy_weather_name,
            )
            shutil.copyfile(_fpath, cls.dummy_weather_file)

        cls.idf = IDFPreprocessor(
            idf_file=cls.dummy_idf_path, timesteps_per_hour=12
        )
        cls.step_size = int(3600.0 / cls.idf.timesteps_per_hour)

        cls.test_sim_config = (
            Config.make_sim_config(
                identifier=[
                    "2df6959cdf502c23f04f3155758d7b678af0c631",  # has full data periods
                ],
                latitude=33.481136,
                longitude=-112.078232,
                start_utc="2018-05-16",
                end_utc="2018-05-26",
                min_sim_period="1D",
                min_chunk_period="30D",
                sim_step_size_seconds=60,
                output_step_size_seconds=300,
            )
            .iloc[0]
            .to_dict()
        )

    @classmethod
    def teardown_class(cls):
        """teardown any state that was previously setup with a call to
        setup_class.
        """
        pass

    @pytest.mark.skip(reason="Redundant with test_simulator.py")
    def test_preprocess(self):
        """
        test that preprocessing produces output file
        """

        prep_idf = self.idf.preprocess(
            sim_config=self.test_sim_config,
            datetime_channel=datetime_channel,
            preprocess_check=False,
        )
        assert os.path.exists(prep_idf)

        # test that preprocessing produces valid IDF output file
        assert self.idf.check_valid_idf(prep_idf) is True
