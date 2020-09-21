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
    full_data_periods = attr.ib(default=[])
    sim_data = attr.ib(default=[])

    def get_full_data_periods(self, expected_period):
        # if self.data has no records then there are no full_data_periods
        _full_data_periods = []
        if not self.data.empty:
            self.data = self.data.sort_values(
                self.spec.datetime_column, ascending=True
            )
            # drop records that are incomplete
            original_len = len(self.data)
            # TODO: can we overwrite self.data?
            _df = (
                self.data.dropna(
                    axis=0, how="any", subset=self.spec.null_check_columns
                )
                .reset_index(drop=True)
                .sort_values(self.spec.datetime_column, ascending=True)
            )

            null_rows = original_len - len(_df)
            logger.info(
                f"Dropped {null_rows} null_rows with no columns={self.spec.null_check_columns}",
            )

            # if null_check_columns is always null then all missing data
            if not _df.empty:

                diffs = _df[self.spec.datetime_column].diff()

                # check for missing records
                missing_start_idx = diffs[
                    diffs > pd.to_timedelta(expected_period)
                ].index.to_list()

                missing_end_idx = [idx - 1 for idx in missing_start_idx] + [
                    len(_df) - 1
                ]
                missing_start_idx = [0] + missing_start_idx
                # ensoure ascending before zip
                missing_start_idx.sort()
                missing_end_idx.sort()

                _full_data_periods = list(
                    zip(
                        pd.to_datetime(
                            _df[self.spec.datetime_column][
                                missing_start_idx
                            ].values,
                            utc=True,
                        ),
                        pd.to_datetime(
                            _df[self.spec.datetime_column][
                                missing_end_idx
                            ].values,
                            utc=True,
                        ),
                    )
                )

        self.full_data_periods = _full_data_periods
