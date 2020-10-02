# created by Tom Stesco tom.s@ecobee.com

import logging
from abc import ABC, abstractmethod

import attr
import pandas as pd
import numpy as np

logger = logging.getLogger(__name__)


@attr.s(kw_only=True)
class DataChannel:

    data = attr.ib()
    spec = attr.ib()

    def get_categories_dict(self):
        """Get dict of all categories for categorical dtypes to sync with models"""
        _cat_dict = {}
        for _col in self.data.columns:
            if isinstance(self.data[_col].dtype, pd.CategoricalDtype):
                _cat_dict[_col] = self.data[_col].dtype.categories

        return _cat_dict
