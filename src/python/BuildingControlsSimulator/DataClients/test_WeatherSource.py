# created by Tom Stesco tom.s@ecobee.com

import logging

import pytest
import os

from BuildingControlsSimulator.DataClients.WeatherSource import WeatherSource


logger = logging.getLogger(__name__)


class TestWeatherSource:
    @classmethod
    def setup_class(cls):
        # initialize with data to avoid pulling multiple times

        cls.weather = WeatherSource(
            nrel_dev_api_key=os.environ.get("NREL_DEV_API_KEY"),
            nrel_dev_email=os.environ.get("NREL_DEV_EMAIL"),
            archive_tmy3_meta=os.environ.get("ARCHIVE_TMY3_META"),
            archive_tmy3_data_dir=os.environ.get("ARCHIVE_TMY3_DATA_DIR"),
            ep_tmy3_cache_dir=os.environ.get("EP_TMY3_CACHE_DIR"),
            simulation_epw_dir=os.environ.get("SIMULATION_EPW_DIR"),
        )

    @classmethod
    def teardown_class(cls):
        """ teardown any state that was previously setup with a call to
        setup_class.
        """
        pass

    def test_get_epw_tmy3(self):
        """
        test that preprocessing produces output file
        """
        lat = 33.481136
        lon = -112.078232
        test_fname = "USA_AZ_Phoenix-Sky.Harbor.Intl.AP.722780_TMY.epw"
        test_fpath = os.path.join(self.weather.ep_tmy3_cache_dir, test_fname)

        # remove test file if previously existing
        if os.path.exists(test_fpath):
            os.remove(test_fpath)
        fpath, fname = self.weather.get_epw_from_nrel(lat, lon)
        assert os.path.exists(fpath)

        # epw file can be read and has correct columns
        data, meta, meta_epw_lines = self.weather.read_epw(fpath)
        cols = data.columns.to_list()
        cols.remove(self.weather.datetime_column)
        assert cols == self.weather.epw_columns

    @pytest.mark.skip()
    def test_get_archive_tmy3(self):
        lat = 33.481136
        lon = -112.078232
        self.weather.get_archive_tmy3(lat, lon)
