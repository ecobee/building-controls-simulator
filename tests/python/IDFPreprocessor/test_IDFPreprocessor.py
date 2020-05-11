#!/usr/bin/env python
# created by Tom Stesco tom.s@ecobee.com

import subprocess
import os
import shlex
import shutil
import logging

import pytest
import pyfmi

from BuildingControlSimulator.BuildingModels.IDFPreprocessor import IDFPreprocessor

logger = logging.getLogger(__name__)


class TestIDFPreprocessor:
    @classmethod
    def setup_class(cls):
        # basic IDF file found in all EnergyPlus installations
        cls.eplus_dir = os.environ["EPLUS_DIR"]
        cls.dummy_idf_name = "Furnace.idf"
        cls.dummy_weather_name = "USA_IL_Chicago-OHare.Intl.AP.725300_TMY3.epw"

        cls.test_data_dir = os.path.join(os.environ["PACKAGE_DIR"], "tests/data")
        cls.ep_version = os.environ["ENERGYPLUS_INSTALL_VERSION"]

        # setup EnergyPlus env
        cmd = "{}/scripts/epvm.sh {}".format(os.environ["PACKAGE_DIR"], cls.ep_version)
        # TODO: running environment script doesnt work
        # subprocess.run(shlex.split(cmd), stdout=subprocess.PIPE, shell=True)

        cls.test_idf_dir = os.path.join(
            cls.test_data_dir, "idf", "v{}".format(cls.ep_version),
        )

        cls.test_fmu_dir = os.path.join(
            cls.test_data_dir, "fmu", "v{}".format(cls.ep_version),
        )

        cls.test_weather_dir = os.path.join(cls.test_data_dir, "weather",)

        # make tests/data/ dirs
        os.makedirs(cls.test_idf_dir, exist_ok=True)
        os.makedirs(os.path.join(cls.test_idf_dir, "preprocessed"), exist_ok=True)
        os.makedirs(cls.test_fmu_dir, exist_ok=True)
        os.makedirs(cls.test_weather_dir, exist_ok=True)

        cls.dummy_idf_file = os.path.join(cls.test_idf_dir, cls.dummy_idf_name)

        cls.dummy_weather_file = os.path.join(
            cls.test_weather_dir, cls.dummy_weather_name
        )

        # if dummy files don't exist copy them from E+ installations
        if not os.path.isfile(cls.dummy_idf_file):
            _fpath = os.path.join(cls.eplus_dir, "ExampleFiles", cls.dummy_idf_name)
            shutil.copyfile(_fpath, cls.dummy_idf_file)

        if not os.path.isfile(cls.dummy_weather_file):
            _fpath = os.path.join(cls.eplus_dir, "WeatherData", cls.dummy_weather_name)
            shutil.copyfile(_fpath, cls.dummy_weather_file)

        cls.idf_preproc = IDFPreprocessor(
            idf_file=cls.dummy_idf_file,
            idf_dir=cls.test_idf_dir,
            fmu_dir=cls.test_fmu_dir,
            ep_version=cls.ep_version,
            timesteps=12,
        )

    @classmethod
    def teardown_class(cls):
        """ teardown any state that was previously setup with a call to
        setup_class.
        """
        pass

    # @pytest.mark.parametrize("eplus_version", ["8-9-0"])
    @pytest.mark.run(order=1)
    def test_preprocess(self):
        """
        test that preprocessing produces output file
        """
        prep_idf = self.idf_preproc.preprocess(
            timesteps_per_hour=self.idf_preproc.timesteps
        )
        assert os.path.exists(prep_idf)

        # test that preprocessing produces valid IDF output file
        assert self.idf_preproc.check_valid_idf(prep_idf) is True

    @pytest.mark.run(order=2)
    def test_make_fmu(self):
        """
        test that make_fmu produces fmu file
        """
        fmu = self.idf_preproc.make_fmu(weather=self.dummy_weather_file)
        assert os.path.exists(fmu)

    @pytest.mark.run(order=3)
    def test_fmu_compliance(self):
        """
        test that fmu file is compliant with FMI.
        """
        # TODO find way to run checker as part of test
        # may need to change EnergyPlusToFMU or FMUComplianceChecker to be non-interactive
        cmd = f'yes | {os.environ["EXT_DIR"]}/FMUComplianceChecker/fmuCheck.linux64 -h {60} -s 172800 {self.idf_preproc.fmu_path}'
        logger.info("FMU compliance checker command:")
        logger.info(cmd)
        # subprocess.run(shlex.split(cmd), stdout=subprocess.PIPE, shell=True)
        pass

    @pytest.mark.run(order=4)
    def test_pyfmi_load_fmu(self):
        """
        test that fmu can be loaded with pyfmi
        """
        model = pyfmi.load_fmu(self.idf_preproc.fmu_path)
        assert model.get_version() == "1.0"

    @pytest.mark.run(order=5)
    def test_simulate_fmu(self):
        """
        test that fmu can be simulated with pyfmi
        """
        model = pyfmi.load_fmu(self.idf_preproc.fmu_path)
        opts = model.simulate_options()
        t_end = 86400.0
        opts["ncp"] = int((t_end / 3600.0) * self.idf_preproc.timesteps)

        res = model.simulate(final_time=t_end, options=opts)

        output = res.result_data.get_data_matrix()

        assert output.shape == (24, 1441)
