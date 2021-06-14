
# 0.4.2 (2021-06-13)

## Features and Improvements
- simplify `.env` setup and usage
- adding archetypal .idf building model geometries
- remove pytest logging of dependency libraries and only show logs from failed tests
- adding `DataClient.generate_dummy_data()` to simplify demo and testing data
- improve `demo_LocalSource.ipynb`
- DataSpecs can now be partially filled to allow for multiple data sources for same specification

## Breaking changes
- ControllerModel now has `options` attribute that defines deadband size
- no longer include outdoor temperature in null check columns to allow for automatic filling of missing weather data

## Bug fixes
- fixed `make_data_directories` usage when no local_cache is given
- fixed `get_local_cache_file` usage when no local_cache is given
- fixed `DataSpec.py` null_check_columns and units
