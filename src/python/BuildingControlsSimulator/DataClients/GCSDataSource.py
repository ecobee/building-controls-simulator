# created by Tom Stesco tom.s@ecobee.com

import logging
from abc import ABC, abstractmethod

import attr

logger = logging.getLogger(__name__)


@attr.s(kw_only=True)
class GCSDataSource(ABC):

    local_cache = attr.ib(default=None)
    gcs_cache = attr.ib(default=None)
    gcp_project = attr.ib(default=None)
    gcs_uri_base = attr.ib(default=None)

    full_data_periods = attr.ib(default={})

    @abstractmethod
    def get_data(self, tstat_ids, start_utc, end_utc):
        pass

    @abstractmethod
    def get_cache(self):
        pass

    @abstractmethod
    def put_cache(self, tstat_ids, start_utc, end_utc):
        pass

    def has_simulation_data(self, tstat_sim_config, full_data_periods):
        _has_simulation_data = {}
        for identifier, tstat in tstat_sim_config.iterrows():
            _has_simulation_data[identifier] = False
            for s, e in full_data_periods[identifier]:
                # check that simulation start_utc and end_utc are within one
                # full data period
                if (
                    s <= tstat.start_utc.to_datetime64()
                    and tstat.end_utc.to_datetime64() <= e
                ):
                    _has_simulation_data[identifier] = True
                    break

        return _has_simulation_data
