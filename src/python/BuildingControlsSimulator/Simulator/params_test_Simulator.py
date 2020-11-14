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
    
"""

test_params_local = []
test_params_gcs_dyd = []
test_params_gbq_flatfiles = []

# if os.environ.get("LOCAL_CACHE_DIR"):
if False:
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
            },
            "controller_model": {
                "is_deadband": True,
                "is_fmu": False,
            },
            "state_estimator_model": {
                "is_low_pass_filter": True,
                "low_pass_filter_alpha": 0.5,
            },
            "expected_result": {
                "mean_thermostat_temperature": 30.96344757080078,
                "mean_thermostat_humidity": 95.2977523803711,
                "output_format_mean_thermostat_temperature": 87.74337768554688,
                "output_format_mean_thermostat_humidity": 95.2977523803711,
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
            },
            "controller_model": {
                "is_deadband": True,
                "is_fmu": False,
            },
            "state_estimator_model": {
                "is_low_pass_filter": True,
                "low_pass_filter_alpha": 0.5,
            },
            "expected_result": {
                "mean_thermostat_temperature": 30.995126724243164,
                "mean_thermostat_humidity": 96.03016662597656,
                "output_format_mean_thermostat_temperature": 87.79023742675781,
                "output_format_mean_thermostat_humidity": 96.03016662597656,
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
                "idf_name": "IL_Chicago_gasfurnace_heatedbsmt_IECC_2018_940_upgraded.idf",
                "epw_name": "USA_IL_Chicago-OHare.Intl.AP.725300_TMY3.epw",
            },
            "controller_model": {
                "is_deadband": True,
                "is_fmu": False,
            },
            "state_estimator_model": {
                "is_low_pass_filter": True,
                "low_pass_filter_alpha": 0.5,
            },
            "expected_result": {
                "mean_thermostat_temperature": 20.913745880126953,
                "mean_thermostat_humidity": 25.508949279785156,
                "output_format_mean_thermostat_temperature": 69.64488983154297,
                "output_format_mean_thermostat_humidity": 25.508949279785156,
            },
        },
        # {
        #     "config": {
        #         "identifier": "2df6959cdf502c23f04f3155758d7b678af0c631",
        #         "latitude": 33.481136,
        #         "longitude": -112.078232,
        #         "start_utc": "2018-05-26",
        #         "end_utc": "2018-06-01",
        #         "min_sim_period": "1D",
        #         "sim_step_size_seconds": 60,
        #         "output_step_size_seconds": 300,
        #     },
        #     "data_client": {
        #         "is_local_source": False,
        #         "is_gcs_source": True,
        #         "is_gbq_source": False,
        #         "gcp_project": os.environ.get("DYD_GOOGLE_CLOUD_PROJECT"),
        #         "gcs_uri_base": os.environ.get("DYD_GCS_URI_BASE"),
        #         "gbq_table": None,
        #         "source_data_spec": DonateYourDataSpec(),
        #         "source_local_cache": os.environ.get("LOCAL_CACHE_DIR"),
        #         "is_local_destination": True,
        #         "is_gcs_destination": False,
        #         "is_gbq_destination": False,
        #         "destination_data_spec": DonateYourDataSpec(),
        #         "destination_local_cache": os.environ.get("LOCAL_CACHE_DIR"),
        #     },
        #     "building_model": {
        #         "is_energyplus_building": True,
        #         "idf_name": "AZ_Phoenix_gasfurnace_crawlspace_IECC_2018_cycles_940_upgraded.idf",
        #         "epw_name": "USA_AZ_Phoenix-Sky.Harbor.Intl.AP.722780_TMY3.epw",
        #     },
        #     "controller_model": {
        #         "is_deadband": True,
        #         "is_fmu": False,
        #     },
        #     "state_estimator_model": {
        #         "is_low_pass_filter": True,
        #         "low_pass_filter_alpha": 0.5,
        #     },
        #     "expected_result": {
        #         "mean_thermostat_temperature": 30.995126724243164,
        #         "mean_thermostat_humidity": 96.03016662597656,
        #         "output_format_mean_thermostat_temperature": 87.79023742675781,
        #         "output_format_mean_thermostat_humidity": 96.03016662597656,
        #     },
        # },
    ]

test_params = (
    test_params_local + test_params_gcs_dyd + test_params_gbq_flatfiles
)