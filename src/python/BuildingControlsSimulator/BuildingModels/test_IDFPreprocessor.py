#!/usr/bin/env python
# created by Tom Stesco tom.s@ecobee.com

import subprocess
import os
import shutil
import logging

import pytest
import pyfmi

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
        # cls.eplus_dir = os.environ.get("EPLUS_DIR")
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

        cls.idf = IDFPreprocessor(idf_file=cls.dummy_idf_path,)
        cls.step_size = int(3600.0 / cls.idf.timesteps)

    @classmethod
    def teardown_class(cls):
        """ teardown any state that was previously setup with a call to
        setup_class.
        """
        pass

    def test_preprocess(self):
        """
        test that preprocessing produces output file
        """
        prep_idf = self.idf.preprocess(timesteps_per_hour=self.idf.timesteps)
        assert os.path.exists(prep_idf)

        # test that preprocessing produces valid IDF output file
        assert self.idf.check_valid_idf(prep_idf) is True

    def test_make_fmu(self):
        """
        test that make_fmu produces fmu file
        """
        fmu = self.idf.make_fmu(weather=self.dummy_weather_file)
        assert os.path.exists(fmu)

    def test_fmu_compliance(self):
        """
        test that fmu file is compliant with FMI.
        """
        # use `bash expect` to run non-interactive
        cmd = """
        bash expect 'Press enter to continue.' {{ send '\r' }} |
        {}/FMUComplianceChecker/fmuCheck.linux64 -h {} -s 172800 -o {} {}
        """.format(
            os.environ.get("EXT_DIR"),
            self.step_size,
            os.path.join(
                os.environ.get("OUTPUT_DIR"), "compliance_check_output.csv"
            ),
            self.idf.fmu_path,
        )

        logger.info("FMU compliance checker command:")
        logger.info(cmd)
        # shlex causes FMUComplianceChecker to run with options, use cmd string
        out = subprocess.run(
            cmd, shell=True, capture_output=False, text=True, input="\n"
        )

        assert out.returncode == 0

    def test_pyfmi_load_fmu(self):
        """
        test that fmu can be loaded with pyfmi
        """
        model = pyfmi.load_fmu(self.idf.fmu_path)
        assert model.get_version() == "1.0"

    def test_simulate_fmu(self):
        """
        test that fmu can be simulated with pyfmi
        """
        model = pyfmi.load_fmu(self.idf.fmu_path)
        opts = model.simulate_options()
        t_end = 86400.0
        opts["ncp"] = int(t_end / self.step_size)

        res = model.simulate(final_time=t_end, options=opts)

        output = res.result_data.get_data_matrix()

        assert output.shape == (24, opts["ncp"] + 1)
