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
    def get_data(self, sim_config):
        pass

    def put_cache(self, _df, local_cache_path):
        # only store cache if set local_cache dir
        if self.local_cache_path:
            os.makedirs(os.path.dirname(local_cache_path), exist_ok=True)
            # explictly infer compression from source file extension
            _df.to_csv(local_cache_path, compression="infer")

    def get_local_cache_path(self, identifier):
        return os.path.join(
            self.local_cache,
            self.source_name,
            "{}.{}".format(identifier, self.file_extension),
        )

    def get_local_cache(self, local_cache_path):
        # cache_file = os.path.join(
        #     self.local_cache,
        #     self.source_name,
        #     "{}.{}".format(identifier, self.file_extension),
        # )
        if os.path.exists(local_cache_path):
            _df = pd.read_csv(
                local_cache_path, usecols=self.data_spec.full.columns,
            )

        else:
            _df = self.get_empty_df()

        return _df

    def get_empty_df(self):
        return pd.DataFrame([], columns=self.data_spec.full.columns)
