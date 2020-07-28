# created by Tom Stesco tom.s@ecobee.com

import logging
from abc import ABC, abstractmethod

import attr
import numpy as np

logger = logging.getLogger(__name__)


@attr.s(kw_only=True)
class DataSource(ABC):

    local_cache = attr.ib(default=None)
    full_data_periods = attr.ib(default={})
    data = attr.ib(default={})

    @abstractmethod
    def get_data(self, tstat_ids, start_utc, end_utc):
        pass

    @abstractmethod
    def get_cache(self):
        pass

    @abstractmethod
    def put_cache(self, tstat_ids, start_utc, end_utc):
        pass

    @staticmethod
    def F2C(temp_F):
        return (temp_F - 32) * 5 / 9
