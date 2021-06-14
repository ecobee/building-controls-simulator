#!/usr/bin/env python
# created by Tom Stesco tom.s@ecobee.com

import subprocess
import os
import shutil
import logging
import pytz

import pytest
import pyfmi
import pandas as pd
import numpy as np

from BuildingControlsSimulator.BuildingModels.IDFPreprocessor import IDFPreprocessor
from BuildingControlsSimulator.BuildingModels.EnergyPlusBuildingModel import (
    EnergyPlusBuildingModel,
)
from BuildingControlsSimulator.DataClients.DataStates import STATES
from BuildingControlsSimulator.DataClients.DataSpec import Internal
from BuildingControlsSimulator.Simulator.Config import Config
from BuildingControlsSimulator.DataClients.DataClient import DataClient
from BuildingControlsSimulator.DataClients.LocalSource import LocalSource
from BuildingControlsSimulator.DataClients.LocalDestination import LocalDestination
from BuildingControlsSimulator.DataClients.DataSpec import DonateYourDataSpec

logger = logging.getLogger(__name__)


class TestEnergyPlusBuildingModel:
    @classmethod
    def setup_class(cls):
        cls.eplus_version = os.environ["ENERGYPLUS_INSTALL_VERSION"]

        # basic IDF file found in all EnergyPlus installations
        # make test/ dirs
        EnergyPlusBuildingModel.make_directories()

        cls.step_size = 300


    # pytest requires the obj containing the params to be called "request"
    @pytest.fixture(
        params=[
            (
                "Furnace.idf",
                "USA_IL_Chicago-OHare.Intl.AP.725300_TMY3.epw",
            ),
        ]
    )
    def building_model(self, request):
        # if dummy files don't exist copy them from E+ installations
        dummy_epw_name = request.param[1]
        dummy_epw_path = os.path.join(os.environ.get("WEATHER_DIR"), dummy_epw_name)
        if not os.path.isfile(dummy_epw_path):
            _fpath = os.path.join(
                os.environ.get("EPLUS_DIR"),
                "WeatherData",
                dummy_epw_name,
            )
            shutil.copyfile(_fpath, dummy_epw_path)

        # if dummy files don't exist copy them from E+ installations
        dummy_idf_name = request.param[0]
        dummy_idf_path = os.path.join(os.environ.get("IDF_DIR"), dummy_idf_name)
        if not os.path.isfile(dummy_idf_path):
            _fpath = os.path.join(
                os.environ.get("EPLUS_DIR"), "ExampleFiles", dummy_idf_name
            )
            shutil.copyfile(_fpath, dummy_idf_path)
        return EnergyPlusBuildingModel(
            idf=IDFPreprocessor(
                idf_file=dummy_idf_path,
                init_temperature=20.0,
            ),
            epw_path=dummy_epw_path,
            step_size_seconds=300,
        )

    @pytest.fixture
    def test_sim_config(self):
        return (
            Config.make_sim_config(
                identifier=[
                    "DYD_dummy_data",
                ],  # has full data periods
                latitude=41.8781,
                longitude=-87.6298,
                start_utc="2018-01-01",
                end_utc="2018-01-04",
                min_sim_period="1D",
                sim_step_size_seconds=300,
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

    def test_energyplus_accessible(self):
        """test that energyplus version is test version and is accessible"""
        cmd = "energyplus -v"
        out = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        if self.eplus_version == "8-9-0":
            assert out.stdout == "EnergyPlus, Version 8.9.0-40101eaafd\n"
        elif self.eplus_version == "9-4-0":
            assert out.stdout == "EnergyPlus, Version 9.4.0-998c4b761e\n"
        else:
            raise ValueError(f"Untested version of energyplus: {self.eplus_version}")

    @pytest.mark.skip(reason="Redundant with test_simulator.py")
    @pytest.mark.usefixtures("building_model")
    def test_preprocess(self, test_sim_config, building_model):
        """test that preprocessing produces output file"""
        # datetime_channel=

        prep_idf = building_model.idf.preprocess(
            sim_config=test_sim_config,
            preprocess_check=False,
            datetime_channel=datetime_channel,
        )
        assert os.path.exists(prep_idf)

        # test that preprocessing produces valid IDF output file
        assert building_model.idf.check_valid_idf(prep_idf) is True

    @pytest.mark.skip(reason="Redundant with test_simulator.py")
    @pytest.mark.usefixtures("building_model")
    def test_make_fmu(self, test_sim_config, building_model):
        """test that make_fmu produces fmu file"""
        dc = DataClient(
            source=LocalSource(
                local_cache=os.environ.get("LOCAL_CACHE_DIR"),
                data_spec=DonateYourDataSpec(),
            ),
            destination=LocalDestination(
                local_cache=os.environ.get("LOCAL_CACHE_DIR"),
                data_spec=DonateYourDataSpec(),
            ),
            nrel_dev_api_key=os.environ.get("NREL_DEV_API_KEY"),
            nrel_dev_email=os.environ.get("NREL_DEV_EMAIL"),
            archive_tmy3_meta=os.environ.get("ARCHIVE_TMY3_META"),
            archive_tmy3_data_dir=os.environ.get("ARCHIVE_TMY3_DATA_DIR"),
            ep_tmy3_cache_dir=os.environ.get("EP_TMY3_CACHE_DIR"),
            simulation_epw_dir=os.environ.get("SIMULATION_EPW_DIR"),
        )
        dc.sim_config = test_sim_config
        dc.get_data()

        fmu = building_model.create_model_fmu(
            sim_config=test_sim_config,
            weather_channel=dc.weather,
            datetime_channel=dc.datetime,
        )
        assert os.path.exists(fmu)

        # @pytest.mark.usefixtures("building_model")
        # def test_fmu_compliance(self, building_model):
        """test that fmu file is compliant with FMI."""
        output_path = os.path.join(
            os.environ.get("OUTPUT_DIR"), "compliance_check_output.csv"
        )
        # use `bash expect` to run non-interactive
        # Note: if this test fails check ./Output_EPExport_Slave/Furnace_prep.err
        cmd = (
            "expect 'Press enter to continue.' {{ send '\r' }} |"
            f' {os.environ.get("EXT_DIR")}/FMUComplianceChecker/fmuCheck.linux64'
            f" -h {self.step_size}"
            " -s 172800"
            f" -o {output_path} {building_model.fmu_path}"
        )
        logger.info("FMU compliance checker command:")
        logger.info(cmd)
        # shlex causes FMUComplianceChecker to run with options, use cmd string
        out = subprocess.run(
            cmd, shell=True, capture_output=False, text=True, input="\n"
        )

        assert out.returncode == 0

    @pytest.mark.skip(reason="Redundant with test_simulator.py.")
    @pytest.mark.usefixtures("building_model")
    def test_pyfmi_load_fmu(self, building_model):
        """test that fmu can be loaded with pyfmi"""
        fmu = pyfmi.load_fmu(building_model.fmu_path)
        assert fmu.get_version() == "1.0"

    @pytest.mark.skip(reason="Redundant with test_simulator.py")
    @pytest.mark.usefixtures("building_model")
    def test_simulate_fmu(self, building_model):
        """test that fmu can be simulated with pyfmi

        Note: if this test fails check ./Output_EPExport_Slave/Furnace_prep.err
        """
        fmu = pyfmi.load_fmu(building_model.fmu_path)
        opts = fmu.simulate_options()
        t_start = 0.0
        t_end = 86400.0
        opts["ncp"] = int(t_end / self.step_size)

        res = fmu.simulate(start_time=t_start, final_time=t_end, options=opts)

        output = res.result_data.get_data_matrix()

        assert output.shape == (30, opts["ncp"] + 1)

    @pytest.mark.skip(
        reason="Segfaults when run without PDB breakpoint. Tried fmu.free_instance(), fmu.terminate()"
    )
    def test_step_fmu(self):
        """test that fmu can be simulated with pyfmi

        Note: if this test fails check ./Output_EPExport_Slave/Furnace_prep.err
        """
        fmu = pyfmi.load_fmu(self.building_model.fmu_path)
        t_start = 0
        t_end = 86400.0
        t_step = 300.0
        ns = int(t_end / t_step)

        fmu.initialize(t_start, t_end)
        status = np.full(ns, False, dtype="int8")

        for i in range(ns):
            status[i] = fmu.do_step(
                current_t=t_start,
                step_size=t_step,
                new_step=True,
            )
            t_start += t_step
        logger.info(f"status={all(status == 0)}")

        # fmu.free_instance()
        # status == 0 corresponds to `fmi1_status_ok`
        # see: https://github.com/modelon-community/PyFMI/blob/PyFMI-2.7.4/src/pyfmi/fmil_import.pxd
        assert all(status == 0)

    @pytest.mark.skip(reason="Redundant with test_simulator.py.")
    @pytest.mark.usefixtures("building_model")
    def test_step_model(self, test_sim_config, building_model):
        """test that fmu can be simulated with pyfmi

        Note: if this test fails check ./Output_EPExport_Slave/Furnace_prep.err
        """
        start_utc = pd.Timestamp("2020-01-01", tz="utc")
        t_start = 0
        t_step = 300
        t_end = 86400.0
        ns = int(t_end / t_step)

        building_model.create_model_fmu(
            sim_config=test_sim_config,
            epw_path=building_model.epw_path,
            preprocess_check=False,
        )
        # need to recude t_end because of non-inclusion of last time step
        building_model.initialize(
            start_utc=start_utc,
            t_start=t_start,
            t_end=t_end - t_step,
            t_step=t_step,
            data_spec=Internal(),
            categories_dict={},
        )

        step_control_input = {
            STATES.AUXHEAT1: t_step,
            STATES.AUXHEAT2: 0,
            STATES.AUXHEAT3: 0,
            STATES.COMPCOOL1: 0,
            STATES.COMPCOOL2: 0,
            STATES.COMPHEAT1: 0,
            STATES.COMPHEAT2: 0,
            STATES.FAN_STAGE_ONE: t_step,
            STATES.FAN_STAGE_TWO: 0,
            STATES.FAN_STAGE_THREE: 0,
        }

        step_sensor_input = {STATES.THERMOSTAT_MOTION: False}

        for i in range(ns):
            building_model.do_step(
                t_start=building_model.output[STATES.SIMULATION_TIME][i],
                t_step=t_step,
                step_control_input=step_control_input,
                step_sensor_input=step_sensor_input,
                step_weather_input={},
            )
        assert (
            pytest.approx(33.394825, 0.01)
            == building_model.fmu_output["EAST_ZONE_zone_air_temperature"].mean()
        )
