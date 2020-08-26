# created by Tom Stesco tom.s@ecobee.com

import os
import logging
from abc import ABC, abstractmethod

import attr
import pandas as pd
import numpy as np

logger = logging.getLogger(__name__)


@attr.s(kw_only=True)
class DataSource(ABC):

    file_extension = attr.ib()
    data_spec = attr.ib()
    local_cache = attr.ib(default=os.environ.get("LOCAL_CACHE_DIR"))
    data = attr.ib(default={})
    source_name = attr.ib(default=None)
    full_data_periods = attr.ib(default={})

    @abstractmethod
    def get_data(self, tstat_sim_config):
        pass

    def put_cache(self, _df, identifier):
        # only store cache if set local_cache dir
        if self.local_cache:
            cache_file = self.get_local_cache_file(identifier)
            os.makedirs(os.path.dirname(cache_file), exist_ok=True)
            # explictly infer compression from source file extension
            _df.to_csv(cache_file, compression="infer")

    def get_local_cache_file(self, identifier):
        return os.path.join(
            self.local_cache,
            self.source_name,
            "{}.{}".format(identifier, self.file_extension),
        )

    def get_local_cache(self, identifier):
        cache_file = os.path.join(
            self.local_cache,
            self.source_name,
            "{}.{}".format(identifier, self.file_extension),
        )
        if os.path.exists(cache_file):
            _df = pd.read_csv(cache_file, usecols=self.data_spec.full.columns,)

        else:
            _df = self.get_empty_df()

        return _df

    def get_empty_df(self):
        return pd.DataFrame([], columns=self.data_spec.full.columns)
