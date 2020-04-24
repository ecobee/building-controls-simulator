#!/usr/bin/env python
# created by Tom Stesco tom.s@ecobee.com

import subprocess
import os
import shlex

import pytest
import pyfmi

from BuildingControlSimulator.BuildingModels.IDFPreprocessor import IDFPreprocessor

class TestImports:
    def test_preprocess(self):
        """
        """
        # TODO test different ep versions 
        # print(os.environ["PACKAGE_DIR"])
        # cmd = f'{os.environ["PACKAGE_DIR"]}/scripts/epvm.sh 8-9-0'
        # print(os.environ["IDF_DIR"])
        # TODO: running environment script doesnt work
        # subprocess.run(shlex.split(cmd), stdout=subprocess.PIPE, shell=True)
        # print(os.environ["IDF_DIR"])

        idf = IDFPreprocessor(
            idf_name=f"Furnace_{os.environ['ENERGYPLUS_INSTALL_VERSION']}.idf",
            weather_name="USA_IL_Chicago-OHare.Intl.AP.725300_TMY3.epw"
        )
        # test that preprocessing produces idf prep file
        assert os.path.exists(idf.preprocess())

    def test_make_fmu(self):
        """
        """
        idf = IDFPreprocessor(
            idf_name=f"Furnace_{os.environ['ENERGYPLUS_INSTALL_VERSION']}.idf",
            weather_name="USA_IL_Chicago-OHare.Intl.AP.725300_TMY3.epw"
        )

        # test that make fmu produces fmu file
        assert os.path.exists(idf.make_fmu())

    def test_fmu_compliance(self):
        """
        """
        # TODO find way to run checker as part of test
        #   may need to change EnergyPlusToFMU or FMUComplianceChecker to be non-interactive
        fmu_dir = os.environ["FMU_DIR"]
        fmu_path = os.path.join(fmu_dir, "_test_fmu_8-9-0.fmu")
        cmd = f'yes | {os.environ["EXT_DIR"]}/FMUComplianceChecker/fmuCheck.linux64 -h {60} -s 172800 {fmu_path}'
        print(cmd)
        # subprocess.run(shlex.split(cmd), stdout=subprocess.PIPE, shell=True)
        pass
    
    def test_pyfmi_load_fmu(self):
        """
        """
        fmu_dir = os.environ["FMU_DIR"]
        model = pyfmi.load_fmu(os.path.join(fmu_dir, "_test_fmu_8-9-0.fmu"))
        assert model.get_version == "1.0"

    def test_simulate_fmu(self):
        """
        """
        fmu_dir = os.environ["FMU_DIR"]
        model = pyfmi.load_fmu(os.path.join(fmu_dir, "_test_fmu_8-9-0.fmu"))
        opts = model.simulate_options()
        t_end = 86400.
        opts['ncp'] = int(t_end / 60.)
        res = model.simulate(final_time=t_end, options=opts)
        

