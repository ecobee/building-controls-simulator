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
                "epw_name": "USA_IL_Chicago-OHare.Intl.AP.725300_TMY3.epw",
            },
            "building_model": {
                "is_energyplus_building": True,
                "idf_name": "Furnace.idf",
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
                "mean_thermostat_temperature": 16.975116729736328,
                "mean_thermostat_humidity": 92.66638946533203,
                "output_format_mean_thermostat_temperature": 62.55436706542969,
                "output_format_mean_thermostat_humidity": 92.66638946533203,
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
                "epw_name": "USA_IL_Chicago-OHare.Intl.AP.725300_TMY3.epw",
            },
            "building_model": {
                "is_energyplus_building": True,
                "idf_name": "Furnace.idf",
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
                "mean_thermostat_temperature": 14.182504653930664,
                "mean_thermostat_humidity": 90.9677963256836,
                "output_format_mean_thermostat_temperature": 57.52853775024414,
                "output_format_mean_thermostat_humidity": 90.9677963256836,
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
                "epw_name": "USA_IL_Chicago-OHare.Intl.AP.725300_TMY3.epw",
            },
            "building_model": {
                "is_energyplus_building": True,
                "idf_name": "heatedbsmt_2story_2300sqft_gasfurnace_AC.idf",
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
                "mean_thermostat_temperature": 20.811267852783203,
                "mean_thermostat_humidity": 24.37480926513672,
                "output_format_mean_thermostat_temperature": 69.45946502685547,
                "output_format_mean_thermostat_humidity": 24.37480926513672,
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
                "epw_name": "USA_IL_Chicago-OHare.Intl.AP.725300_TMY3.epw",
            },
            "building_model": {
                "is_energyplus_building": True,
                "idf_name": "heatedbsmt_2story_2300sqft_gasfurnace_AC.idf",
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
                "mean_thermostat_temperature": 21.750398635864258,
                "mean_thermostat_humidity": 75.98658752441406,
                "output_format_mean_thermostat_temperature": 71.1498031616211,
                "output_format_mean_thermostat_humidity": 75.98658752441406,
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
                "epw_name": "USA_IL_Chicago-OHare.Intl.AP.725300_TMY3.epw",
            },
            "building_model": {
                "is_energyplus_building": True,
                "idf_name": "heatedbsmt_2story_2300sqft_gasfurnace_AC.idf",
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
                "mean_thermostat_temperature": 20.449106216430664,
                "mean_thermostat_humidity": 21.244773864746094,
                "output_format_mean_thermostat_temperature": 688.0977783203125,
                "output_format_mean_thermostat_humidity": 21.244773864746094,
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
                "epw_name": "USA_IL_Chicago-OHare.Intl.AP.725300_TMY3.epw",
            },
            "building_model": {
                "is_energyplus_building": True,
                "idf_name": "heatedbsmt_2story_2300sqft_gasfurnace_AC.idf",
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
                "mean_thermostat_temperature": 20.167783737182617,
                "mean_thermostat_humidity": 16.607179641723633,
                "output_format_mean_thermostat_temperature": 683.0032348632812,
                "output_format_mean_thermostat_humidity": 16.607179641723633,
            },
        },
    ]

test_params = test_params_local + test_params_gcs_dyd + test_params_gbq_flatfiles
