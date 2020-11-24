# created by Tom Stesco tom.s@ecobee.com

import logging

import pytest
import pandas as pd
import os
import shutil

from BuildingControlsSimulator.Simulator.Simulator import Simulator
from BuildingControlsSimulator.Simulator.Config import Config
from BuildingControlsSimulator.DataClients.DataClient import DataClient
from BuildingControlsSimulator.DataClients.GCSDYDSource import GCSDYDSource
from BuildingControlsSimulator.DataClients.GCSFlatFilesSource import (
    GCSFlatFilesSource,
)
from BuildingControlsSimulator.DataClients.GBQDataSource import GBQDataSource
from BuildingControlsSimulator.DataClients.LocalSource import LocalSource
from BuildingControlsSimulator.BuildingModels.IDFPreprocessor import (
    IDFPreprocessor,
)
from BuildingControlsSimulator.BuildingModels.EnergyPlusBuildingModel import (
    EnergyPlusBuildingModel,
)
from BuildingControlsSimulator.DataClients.LocalDestination import (
    LocalDestination,
)
from BuildingControlsSimulator.DataClients.DataSpec import (
    DonateYourDataSpec,
    Internal,
    FlatFilesSpec,
)
from BuildingControlsSimulator.ControllerModels.FMIController import (
    FMIController,
)
from BuildingControlsSimulator.ControllerModels.Deadband import Deadband
from BuildingControlsSimulator.DataClients.DataStates import STATES
from BuildingControlsSimulator.StateEstimatorModels.LowPassFilter import (
    LowPassFilter,
)
import BuildingControlsSimulator.Simulator.params_test_Simulator as params

logger = logging.getLogger(__name__)


class TestSimulator:
    @classmethod
    def setup_class(cls):
        # initialize with data to avoid pulling multiple times
        EnergyPlusBuildingModel.make_directories()

    def get_epw_path(self, epw_name):
        # the weather file here does not need to be correct for IDF file as we
        # will be testing permutations and erroneous case

        # if we took the time to supply a full path, might as well try it out
        if os.path.isfile(epw_name):
            return epw_name

        # check WEATHER_DIR
        test_weather_path = os.path.join(
            os.environ.get("WEATHER_DIR"), epw_name
        )
        # if not found search energyplus default weather files
        # these are included in all energyplus installs
        if not os.path.isfile(test_weather_path):
            _fpath = os.path.join(
                os.environ.get("EPLUS_DIR"),
                "WeatherData",
                epw_name,
            )
            if os.path.isfile(_fpath):
                shutil.copyfile(_fpath, test_weather_path)
            else:
                raise ValueError(
                    f"Could not find supplied weather file: {epw_name}"
                )

        return test_weather_path

    def get_idf_path(self, idf_name):
        # the weather file here does not need to be correct for IDF file as we
        # will be testing permutations and erroneous cases

        # if we took the time to supply a full path, might as well try it out
        if os.path.isfile(idf_name):
            return idf_name

        # check IDF_DIR
        test_idf_path = os.path.join(os.environ.get("IDF_DIR"), idf_name)
        # if not found search energyplus default weather files
        # these are included in all energyplus installs
        if not os.path.isfile(test_idf_path):
            _fpath = os.path.join(
                os.environ.get("EPLUS_DIR"),
                "ExampleFiles",
                idf_name,
            )
            if os.path.isfile(_fpath):
                shutil.copyfile(_fpath, test_idf_path)
            else:
                raise ValueError(
                    f"Could not find supplied idf file: {idf_name}"
                )

        return test_idf_path

    def get_fmu(self, fmu_name):
        return (
            f"{os.environ.get('FMU_DIR')}/../fmu-models/deadband/deadband.fmu"
        )

    @classmethod
    def teardown_class(cls):
        """teardown any state that was previously setup with a call to
        setup_class.
        """
        pass

    def get_data_source(self, data_client_params):
        _source = None
        if data_client_params["is_local_source"]:
            _source = LocalSource(
                data_spec=data_client_params["source_data_spec"],
                local_cache=data_client_params["source_local_cache"],
            )
        elif data_client_params["is_gcs_source"]:
            if isinstance(
                data_client_params["source_data_spec"], DonateYourDataSpec
            ):
                _source = GCSDYDSource(
                    gcp_project=data_client_params["gcp_project"],
                    gcs_uri_base=data_client_params["gcs_uri_base"],
                    local_cache=data_client_params["source_local_cache"],
                )
            elif isinstance(
                data_client_params["source_data_spec"], FlatFilesSpec
            ):
                _source = GCSFlatFilesSource(
                    gcp_project=data_client_params["gcp_project"],
                    gcs_uri_base=data_client_params["gcs_uri_base"],
                    local_cache=data_client_params["source_local_cache"],
                )

        elif data_client_params["is_gbq_source"]:
            _source = GBQDataSource(
                data_spec=data_client_params["source_data_spec"],
                gcp_project=data_client_params["gcp_project"],
                gbq_table=data_client_params["gbq_table"],
                local_cache=data_client_params["source_local_cache"],
            )
        return _source

    def get_data_destination(self, data_client_params):
        _dest = None
        if data_client_params["is_local_destination"]:
            _dest = LocalDestination(
                local_cache=data_client_params["destination_local_cache"],
                data_spec=data_client_params["destination_data_spec"],
            )
        return _dest

    def get_building_model(self, building_model_params):
        _building = None
        if building_model_params["is_energyplus_building"]:
            _building = EnergyPlusBuildingModel(
                idf=IDFPreprocessor(
                    idf_file=self.get_idf_path(
                        building_model_params["idf_name"]
                    ),
                    building_config=building_model_params["building_config"],
                    debug=True,
                ),
                fill_epw_path=self.get_epw_path(
                    building_model_params["epw_name"]
                ),
            )

        return _building

    def get_controller_model(self, controller_model_params):
        _controller = None
        if controller_model_params["is_deadband"]:
            _controller = Deadband(deadband=1.0)

        return _controller

    def get_state_estimator_model(self, state_estimator_model_params):
        _state_estimator = None
        if state_estimator_model_params["is_low_pass_filter"]:
            _state_estimator = LowPassFilter(
                alpha_temperature=state_estimator_model_params[
                    "low_pass_filter_alpha"
                ],
                alpha_humidity=state_estimator_model_params[
                    "low_pass_filter_alpha"
                ],
            )

        return _state_estimator

    @pytest.mark.parametrize("test_params", params.test_params)
    def test_simulator(self, test_params):
        _config_params = test_params["config"]
        test_sim_config = Config.make_sim_config(
            identifier=_config_params["identifier"],
            latitude=_config_params["latitude"],
            longitude=_config_params["longitude"],
            start_utc=_config_params["start_utc"],
            end_utc=_config_params["end_utc"],
            min_sim_period=_config_params["min_sim_period"],
            sim_step_size_seconds=_config_params["sim_step_size_seconds"],
            output_step_size_seconds=_config_params[
                "output_step_size_seconds"
            ],
        )

        dc = DataClient(
            source=self.get_data_source(test_params["data_client"]),
            destination=self.get_data_destination(test_params["data_client"]),
            nrel_dev_api_key=os.environ.get("NREL_DEV_API_KEY"),
            nrel_dev_email=os.environ.get("NREL_DEV_EMAIL"),
            archive_tmy3_meta=os.environ.get("ARCHIVE_TMY3_META"),
            archive_tmy3_data_dir=os.environ.get("ARCHIVE_TMY3_DATA_DIR"),
            ep_tmy3_cache_dir=os.environ.get("EP_TMY3_CACHE_DIR"),
            simulation_epw_dir=os.environ.get("SIMULATION_EPW_DIR"),
        )

        # test HVAC data returns dict of non-empty pd.DataFrame
        master = Simulator(
            data_client=dc,
            sim_config=test_sim_config,
            building_models=[
                self.get_building_model(test_params["building_model"])
            ],
            controller_models=[
                self.get_controller_model(test_params["controller_model"])
            ],
            state_estimator_models=[
                self.get_state_estimator_model(
                    test_params["state_estimator_model"]
                )
            ],
        )
        master.simulate(local=True, preprocess_check=False)

        # read back stored output and check it
        sim_name = master.simulations[0].sim_name
        _fpath = os.path.join(
            master.simulations[0].data_client.destination.local_cache,
            master.simulations[0].data_client.destination.operator_name,
            sim_name
            + "."
            + master.simulations[0].data_client.destination.file_extension,
        )
        r_df = pd.read_parquet(_fpath)
        t_ctrl_name = [
            _k
            for _k, _v in master.simulations[
                0
            ].data_client.destination.data_spec.full.spec.items()
            if _v["internal_state"] == STATES.TEMPERATURE_CTRL
        ][0]
        humidity_name = [
            _k
            for _k, _v in master.simulations[
                0
            ].data_client.destination.data_spec.full.spec.items()
            if _v["internal_state"] == STATES.THERMOSTAT_HUMIDITY
        ][0]

        assert (
            pytest.approx(
                test_params["expected_result"]["mean_thermostat_temperature"]
            )
            == master.simulations[0]
            .output[STATES.THERMOSTAT_TEMPERATURE]
            .mean()
        )
        assert (
            pytest.approx(
                test_params["expected_result"]["mean_thermostat_humidity"]
            )
            == master.simulations[0].output[STATES.THERMOSTAT_HUMIDITY].mean()
        )
        assert (
            pytest.approx(
                test_params["expected_result"][
                    "output_format_mean_thermostat_temperature"
                ]
            )
            == r_df[t_ctrl_name].mean()
        )
        assert (
            pytest.approx(
                test_params["expected_result"][
                    "output_format_mean_thermostat_humidity"
                ]
            )
            == r_df[humidity_name].mean()
        )
