# 0.6.0-alpha (2022-03-15)

## Features and Improvements
- update dependencies to latest versions (see diff of requirements.txt)
- DataSpec and conversions support nullable and non-nullable data types in numpy and pandas

## Breaking changes
- Previously undefined behaviour of nullable data types must now be defined in conversions

## Bug fixes
- fixed make_epw_file and adding test_make_epw_file
- fixed DataClient issue with data type conversion after filling nulls
- fixed DataClient.py removal of columns that get truncated to all NA

# 0.5.0-alpha (2021-06-13)

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
- conditional skipping of `DataClient` tests that use external data sources if those sources are not configured
