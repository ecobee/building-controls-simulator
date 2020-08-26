# created by Tom Stesco tom.s@ecobee.com

import os
import logging

import pandas as pd
import attr
import numpy as np

# from google.cloud import storage

from BuildingControlsSimulator.DataClients.DataClient import DataClient
from BuildingControlsSimulator.DataClients.GCSDataSource import GCSDataSource
from BuildingControlsSimulator.DataClients.DataSpec import Internal
from BuildingControlsSimulator.DataClients.SensorsChannel import SensorsChannel
from BuildingControlsSimulator.DataClients.HVACChannel import HVACChannel
from BuildingControlsSimulator.DataClients.WeatherChannel import WeatherChannel


logger = logging.getLogger(__name__)


@attr.s(kw_only=True)
class FlatFilesClient(DataClient):
    """Client for ISM data.
    ISM is implemented as a GCS hosted cache.
    """

    # input variables
    nrel_dev_api_key = attr.ib(default=None)
    nrel_dev_email = attr.ib(default=None)
    archive_tmy3_meta = attr.ib(default=None)
    archive_tmy3_data_dir = attr.ib(
        default=os.environ.get("ARCHIVE_TMY3_DATA_DIR")
    )
    ep_tmy3_cache_dir = attr.ib(default=os.environ.get("EP_TMY3_CACHE_DIR"))
    simulation_epw_dir = attr.ib(default=os.environ.get("SIMULATION_EPW_DIR"))

    # state variabels
    # data_channels = attr.ib(default=None)
    meta_gs_uri = attr.ib(default=None)
    # data_spec = attr.ib()
    sources = attr.ib()

    def __attrs_post_init__(self):
        # first, post init class specification
        if self.local_cache and os.path.exists(self.local_cache):
            self.local_data_dir = attr.ib(
                default=os.path.join(self.local_cache, self.data_source_name)
            )
            self.local_meta_dir = attr.ib(
                default=os.path.join(self.local_data_dir, "meta")
            )
            # for local cache save files on local machine
            os.makedirs(self.local_data_dir, exist_ok=True)
            os.makedirs(self.local_meta_dir, exist_ok=True)

        # self.data_source = GCSDataSource(data_spec=self.data_spec)

    def get_data(self, tstat_sim_config):
        # first cast to utc timestamp
        # DYD uses UTC
        start_utc = pd.to_datetime(
            tstat_sim_config["start_utc"], utc=True, infer_datetime_format=True
        )
        end_utc = pd.to_datetime(
            tstat_sim_config["end_utc"], utc=True, infer_datetime_format=True
        )
        # check for invalid start/end combination
        invalid = tstat_sim_config[
            tstat_sim_config["end_utc"] <= tstat_sim_config["start_utc"]
        ]

        if not invalid.empty:
            raise ValueError(
                "tstat_sim_config contains invalid start_utc >= end_utc."
            )

        # supporting cross year simulations would require loading both years
        if np.any(end_utc.dt.year != start_utc.dt.year):
            raise ValueError("start_utc must be in same year as end_utc.")

        years_supported = [2016, 2017, 2018, 2019]
        if np.any(~start_utc.dt.year.isin(years_supported)):
            raise ValueError(
                f"start_utc must be in supported years: {years_supported}"
            )

        # HVAC and weather data are stored in same files in DYD
        # DYDHVACSource performs read and feeds to weather.from_dyd_hvac()
        # self.hvac.get_data(tstat_sim_config)
        # self.weather.get_data(
        #     tstat_sim_config, self.hvac.weather_data,
        # )

        # format tstat_sim_config with data for downloading data
        # and defining data channels
        # tstat_sim_config = self.get_gcs_uri(tstat_sim_config)

        # download each data source
        # convert to internal flat format

        _data = {
            identifier: pd.DataFrame([], columns=[Internal.datetime_column])
            for identifier in tstat_sim_config.index
        }
        for _s in self.sources:
            # load from cache or download data from source
            _data_dict = _s.get_data(tstat_sim_config)
            for tstat, _df in _data_dict.items():
                # joining on datetime column with the initial empty df having
                # only the datetime_column causes new columns to be added
                # and handles missing data in any data sets
                if not _df.empty:
                    _data[tstat] = _data[tstat].merge(
                        _df, how="outer", on=Internal.datetime_column,
                    )
                else:
                    logging.info(
                        "EMPTY SOURCE: tstat={}, source={}".format(tstat, _s)
                    )
                    if _data[tstat].empty:
                        _data[tstat] = Internal.get_empty_df()

        # split into data channels
        for identifier, tstat in tstat_sim_config.iterrows():
            self.hvac[identifier] = HVACChannel(
                data=_data[identifier][
                    [Internal.datetime_column] + Internal.hvac.columns
                ],
                spec=Internal.hvac,
            )
            self.hvac[identifier].get_full_data_periods(expected_period="5M")

            self.sensors[identifier] = SensorsChannel(
                data=_data[identifier][
                    [Internal.datetime_column] + Internal.sensors.columns
                ],
                spec=Internal.sensors,
            )
            self.sensors[identifier].get_full_data_periods(
                expected_period="5M"
            )

            self.weather[identifier] = WeatherChannel(
                data=_data[identifier][
                    [Internal.datetime_column] + Internal.weather.columns
                ],
                spec=Internal.weather,
                archive_tmy3_data_dir=self.archive_tmy3_data_dir,
                ep_tmy3_cache_dir=self.ep_tmy3_cache_dir,
                simulation_epw_dir=self.simulation_epw_dir,
            )
            self.weather[identifier].get_full_data_periods(
                expected_period="5M"
            )
            # post-processing of data channels

            self.weather[identifier].make_epw_file(tstat=tstat)

    def get_metadata(self):
        return pd.read_csv(self.meta_gs_uri).drop_duplicates(
            subset=["Identifier"]
        )
