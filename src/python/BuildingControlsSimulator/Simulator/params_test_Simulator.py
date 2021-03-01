# created by Tom Stesco tom.s@ecobee.com
import os
from BuildingControlsSimulator.DataClients.DataSpec import (
    DonateYourDataSpec,
    Internal,
    FlatFilesSpec,
)

"""
Models:
    Furnace.idf:
        This model is not realistic at all, but is included in every
        EnergyPlus installation and for this reason is used to test
        basic I/O and functionality of the simulation platform.
    heatedbsmt_2story_2300sqft_gasfurnace_AC.idf:
        Template model for testing `IDFPreprocessor` features.
    
"""

test_params_local = []
test_params_gcs_dyd = []
test_params_gbq_flatfiles = []

if os.environ.get("LOCAL_CACHE_DIR"):
    test_params_local = [
        {
            "config": {
                "identifier": "DYD_dummy_data",
                "latitude": 41.8781,
                "longitude": -87.6298,
                "start_utc": "2018-05-16",
                "end_utc": "2018-06-01",
                "min_sim_period": "1D",
                "sim_step_size_seconds": 900,
                "output_step_size_seconds": 300,
            },
            "data_client": {
                "is_local_source": True,
                "is_gcs_source": False,
                "is_gbq_source": False,
                "gcp_project": None,
                "gcs_uri_base": None,
                "gbq_table": None,
                "source_data_spec": DonateYourDataSpec(),
                "source_local_cache": os.environ.get("LOCAL_CACHE_DIR"),
                "is_local_destination": True,
                "is_gcs_destination": False,
                "is_gbq_destination": False,
                "destination_data_spec": DonateYourDataSpec(),
                "destination_local_cache": os.environ.get("LOCAL_CACHE_DIR"),
            },
            "building_model": {
                "is_energyplus_building": True,
                "idf_name": "Furnace.idf",
                "epw_name": "USA_IL_Chicago-OHare.Intl.AP.725300_TMY3.epw",
                "building_config": {},
                "step_size_seconds": 900,
            },
            "controller_model": {
                "is_deadband": True,
                "is_fmu": False,
                "step_size_seconds": 900,
            },
            "state_estimator_model": {
                "is_low_pass_filter": True,
                "low_pass_filter_alpha": 0.5,
            },
            "expected_result": {
                "mean_thermostat_temperature": 31.378896713256836,
                "mean_thermostat_humidity": 94.83988189697266,
                "output_format_mean_thermostat_temperature": 88.48159790039062,
                "output_format_mean_thermostat_humidity": 94.83988189697266,
            },
        },
        {
            "config": {
                "identifier": "DYD_dummy_data",
                "latitude": 41.8781,
                "longitude": -87.6298,
                "start_utc": "2018-05-16",
                "end_utc": "2018-06-01",
                "min_sim_period": "1D",
                "sim_step_size_seconds": 60,
                "output_step_size_seconds": 300,
            },
            "data_client": {
                "is_local_source": True,
                "is_gcs_source": False,
                "is_gbq_source": False,
                "gcp_project": None,
                "gcs_uri_base": None,
                "gbq_table": None,
                "source_data_spec": DonateYourDataSpec(),
                "source_local_cache": os.environ.get("LOCAL_CACHE_DIR"),
                "is_local_destination": True,
                "is_gcs_destination": False,
                "is_gbq_destination": False,
                "destination_data_spec": DonateYourDataSpec(),
                "destination_local_cache": os.environ.get("LOCAL_CACHE_DIR"),
            },
            "building_model": {
                "is_energyplus_building": True,
                "idf_name": "Furnace.idf",
                "epw_name": "USA_IL_Chicago-OHare.Intl.AP.725300_TMY3.epw",
                "building_config": {},
                "step_size_seconds": 60,
            },
            "controller_model": {
                "is_deadband": True,
                "is_fmu": False,
                "step_size_seconds": 60,
            },
            "state_estimator_model": {
                "is_low_pass_filter": True,
                "low_pass_filter_alpha": 0.5,
            },
            "expected_result": {
                "mean_thermostat_temperature": 31.407203674316406,
                "mean_thermostat_humidity": 95.72138977050781,
                "output_format_mean_thermostat_temperature": 88.53276062011719,
                "output_format_mean_thermostat_humidity": 95.72138977050781,
            },
        },
    ]

if os.environ.get("DYD_GCS_URI_BASE"):
    test_params_gcs_dyd = [
        {
            "config": {
                "identifier": "2e7467a283eaa1ab1d435bca6d7a36017e0fabf6",
                "latitude": 41.8781,
                "longitude": -87.6298,
                "start_utc": "2018-01-10",
                "end_utc": "2018-01-17",
                "min_sim_period": "1D",
                "sim_step_size_seconds": 60,
                "output_step_size_seconds": 300,
            },
            "data_client": {
                "is_local_source": False,
                "is_gcs_source": True,
                "is_gbq_source": False,
                "gcp_project": os.environ.get("DYD_GOOGLE_CLOUD_PROJECT"),
                "gcs_uri_base": os.environ.get("DYD_GCS_URI_BASE"),
                "gbq_table": None,
                "source_data_spec": DonateYourDataSpec(),
                "source_local_cache": os.environ.get("LOCAL_CACHE_DIR"),
                "is_local_destination": True,
                "is_gcs_destination": False,
                "is_gbq_destination": False,
                "destination_data_spec": DonateYourDataSpec(),
                "destination_local_cache": os.environ.get("LOCAL_CACHE_DIR"),
            },
            "building_model": {
                "is_energyplus_building": True,
                "idf_name": "heatedbsmt_2story_2300sqft_gasfurnace_AC.idf",
                "epw_name": "USA_IL_Chicago-OHare.Intl.AP.725300_TMY3.epw",
                "step_size_seconds": 60,
                "building_config": {
                    "infiltration_ventilation": {
                        "ach50": 10,
                        "wsf": 0.6,
                    },
                    "insulation_r_si": {
                        "Exterior Roof": 1.0,
                        "Interior Ceiling": 6.7,
                        "Interior Floor": 0.75,
                        "Exterior Wall": 5.25,
                        "Exterior Floor": 5.0,
                    },
                    "windows": {
                        "u_factor": 0.8,
                        "solar_heat_gain": 0.30,
                        "visible_transmittance": 0.60,
                    },
                    "hvac": {
                        "heating_stages": 1,
                        "heating_equipment": "gas_furnace",
                        "heating_sizing_factor": 0.9,
                        "cooling_stages": 1,
                        "cooling_equipment": "dx_ac",
                        "cooling_sizing_factor": 0.9,
                    },
                    "thermal_mass": 1e7,
                },
            },
            "controller_model": {
                "is_deadband": True,
                "is_fmu": False,
                "step_size_seconds": 60,
            },
            "state_estimator_model": {
                "is_low_pass_filter": True,
                "low_pass_filter_alpha": 0.5,
            },
            "expected_result": {
                "mean_thermostat_temperature": 20.911911010742188,
                "mean_thermostat_humidity": 24.214298248291016,
                "output_format_mean_thermostat_temperature": 69.64139556884766,
                "output_format_mean_thermostat_humidity": 24.214298248291016,
            },
        },
        {
            "config": {
                "identifier": "2e7467a283eaa1ab1d435bca6d7a36017e0fabf6",
                "latitude": 41.8781,
                "longitude": -87.6298,
                "start_utc": "2018-06-10",
                "end_utc": "2018-06-17",
                "min_sim_period": "1D",
                "sim_step_size_seconds": 60,
                "output_step_size_seconds": 300,
            },
            "data_client": {
                "is_local_source": False,
                "is_gcs_source": True,
                "is_gbq_source": False,
                "gcp_project": os.environ.get("DYD_GOOGLE_CLOUD_PROJECT"),
                "gcs_uri_base": os.environ.get("DYD_GCS_URI_BASE"),
                "gbq_table": None,
                "source_data_spec": DonateYourDataSpec(),
                "source_local_cache": os.environ.get("LOCAL_CACHE_DIR"),
                "is_local_destination": True,
                "is_gcs_destination": False,
                "is_gbq_destination": False,
                "destination_data_spec": DonateYourDataSpec(),
                "destination_local_cache": os.environ.get("LOCAL_CACHE_DIR"),
            },
            "building_model": {
                "is_energyplus_building": True,
                "idf_name": "heatedbsmt_2story_2300sqft_gasfurnace_AC.idf",
                "epw_name": "USA_IL_Chicago-OHare.Intl.AP.725300_TMY3.epw",
                "step_size_seconds": 60,
                "building_config": {
                    "infiltration_ventilation": {
                        "ach50": 10,
                        "wsf": 0.6,
                    },
                    "insulation_r_si": {
                        "Exterior Roof": 1.0,
                        "Interior Ceiling": 6.7,
                        "Interior Floor": 0.75,
                        "Exterior Wall": 5.25,
                        "Exterior Floor": 5.0,
                    },
                    "windows": {
                        "u_factor": 0.8,
                        "solar_heat_gain": 0.30,
                        "visible_transmittance": 0.60,
                    },
                    "hvac": {
                        "heating_stages": 1,
                        "heating_equipment": "gas_furnace",
                        "heating_sizing_factor": 0.9,
                        "cooling_stages": 1,
                        "cooling_equipment": "dx_ac",
                        "cooling_sizing_factor": 0.9,
                    },
                    "thermal_mass": 1e7,
                },
            },
            "controller_model": {
                "is_deadband": True,
                "is_fmu": False,
                "step_size_seconds": 60,
            },
            "state_estimator_model": {
                "is_low_pass_filter": True,
                "low_pass_filter_alpha": 0.5,
            },
            "expected_result": {
                "mean_thermostat_temperature": 32.04988479614258,
                "mean_thermostat_humidity": 44.438236236572266,
                "output_format_mean_thermostat_temperature": 89.6878433227539,
                "output_format_mean_thermostat_humidity": 44.438236236572266,
            },
        },
    ]

if os.environ.get("FLATFILES_GBQ_TABLE"):
    test_params_gbq_flatfiles = [
        {
            "config": {
                "identifier": os.environ.get("TEST_GBQ_FF_IDENTIFIER"),
                "latitude": 41.8781,
                "longitude": -87.6298,
                "start_utc": "2019-01-14",
                "end_utc": "2019-01-18",
                "min_sim_period": "1D",
                "sim_step_size_seconds": 60,
                "output_step_size_seconds": 300,
            },
            "data_client": {
                "is_local_source": False,
                "is_gcs_source": False,
                "is_gbq_source": True,
                "gcp_project": os.environ.get("DYD_GOOGLE_CLOUD_PROJECT"),
                "gcs_uri_base": None,
                "gbq_table": os.environ.get("FLATFILES_GBQ_TABLE"),
                "source_data_spec": FlatFilesSpec(),
                "source_local_cache": os.environ.get("LOCAL_CACHE_DIR"),
                "is_local_destination": True,
                "is_gcs_destination": False,
                "is_gbq_destination": False,
                "destination_data_spec": FlatFilesSpec(),
                "destination_local_cache": os.environ.get("LOCAL_CACHE_DIR"),
            },
            "building_model": {
                "is_energyplus_building": True,
                "idf_name": "heatedbsmt_2story_2300sqft_gasfurnace_AC.idf",
                "epw_name": "USA_IL_Chicago-OHare.Intl.AP.725300_TMY3.epw",
                "step_size_seconds": 60,
                "building_config": {
                    "infiltration_ventilation": {
                        "ach50": 10,
                        "wsf": 0.6,
                    },
                    "insulation_r_si": {
                        "Exterior Roof": 1.0,
                        "Interior Ceiling": 6.7,
                        "Interior Floor": 0.75,
                        "Exterior Wall": 5.25,
                        "Exterior Floor": 5.0,
                    },
                    "windows": {
                        "u_factor": 0.8,
                        "solar_heat_gain": 0.30,
                        "visible_transmittance": 0.60,
                    },
                    "hvac": {
                        "heating_stages": 1,
                        "heating_equipment": "gas_furnace",
                        "heating_sizing_factor": 0.9,
                        "cooling_stages": 1,
                        "cooling_equipment": "dx_ac",
                        "cooling_sizing_factor": 0.9,
                    },
                    "thermal_mass": 1e7,
                },
            },
            "controller_model": {
                "is_deadband": True,
                "is_fmu": False,
                "step_size_seconds": 60,
            },
            "state_estimator_model": {
                "is_low_pass_filter": True,
                "low_pass_filter_alpha": 0.2,
            },
            "expected_result": {
                "mean_thermostat_temperature": 20.887479782104492,
                "mean_thermostat_humidity": 20.74267578125,
                "output_format_mean_thermostat_temperature": 695.9857788085938,
                "output_format_mean_thermostat_humidity": 20.74267578125,
            },
        },
        {
            "config": {
                "identifier": os.environ.get("TEST_GBQ_FF_IDENTIFIER_2"),
                "latitude": 51.217373,
                "longitude": -114.296019,
                "start_utc": "2019-03-09",
                "end_utc": "2019-03-15",
                "min_sim_period": "1D",
                "sim_step_size_seconds": 60,
                "output_step_size_seconds": 300,
            },
            "data_client": {
                "is_local_source": False,
                "is_gcs_source": False,
                "is_gbq_source": True,
                "gcp_project": os.environ.get("DYD_GOOGLE_CLOUD_PROJECT"),
                "gcs_uri_base": None,
                "gbq_table": os.environ.get("FLATFILES_GBQ_TABLE"),
                "source_data_spec": FlatFilesSpec(),
                "source_local_cache": os.environ.get("LOCAL_CACHE_DIR"),
                "is_local_destination": True,
                "is_gcs_destination": False,
                "is_gbq_destination": False,
                "destination_data_spec": FlatFilesSpec(),
                "destination_local_cache": os.environ.get("LOCAL_CACHE_DIR"),
            },
            "building_model": {
                "is_energyplus_building": True,
                "idf_name": "heatedbsmt_2story_2300sqft_gasfurnace_AC.idf",
                "epw_name": "USA_IL_Chicago-OHare.Intl.AP.725300_TMY3.epw",
                "step_size_seconds": 60,
                "building_config": {
                    "infiltration_ventilation": {
                        "ach50": 10,
                        "wsf": 0.6,
                    },
                    "insulation_r_si": {
                        "Exterior Roof": 1.0,
                        "Interior Ceiling": 6.7,
                        "Interior Floor": 0.75,
                        "Exterior Wall": 5.25,
                        "Exterior Floor": 5.0,
                    },
                    "windows": {
                        "u_factor": 0.8,
                        "solar_heat_gain": 0.30,
                        "visible_transmittance": 0.60,
                    },
                    "hvac": {
                        "heating_stages": 1,
                        "heating_equipment": "gas_furnace",
                        "heating_sizing_factor": 0.9,
                        "cooling_stages": 1,
                        "cooling_equipment": "dx_ac",
                        "cooling_sizing_factor": 0.9,
                    },
                    "thermal_mass": 1e7,
                },
            },
            "controller_model": {
                "is_deadband": True,
                "is_fmu": False,
                "step_size_seconds": 60,
            },
            "state_estimator_model": {
                "is_low_pass_filter": True,
                "low_pass_filter_alpha": 0.2,
            },
            "expected_result": {
                "mean_thermostat_temperature": 20.319211959838867,
                "mean_thermostat_humidity": 16.502723693847656,
                "output_format_mean_thermostat_temperature": 685.7371826171875,
                "output_format_mean_thermostat_humidity": 16.502723693847656,
            },
        },
    ]

test_params = test_params_local + test_params_gcs_dyd + test_params_gbq_flatfiles
