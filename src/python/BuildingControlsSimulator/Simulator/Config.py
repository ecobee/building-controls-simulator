# created by Tom Stesco tom.s@ecobee.com
from collections.abc import Iterable


import pandas as pd
import numpy as np


class Config:
    @staticmethod
    def make_sim_config(
        identifier,
        latitude,
        longitude,
        start_utc,
        end_utc,
        min_sim_period,
        step_size_minutes,
        min_chunk_period="30D",
    ):
        # first make sure identifier is iterable and wrapped if a str
        if not isinstance(identifier, Iterable) or isinstance(identifier, str):
            identifier = [identifier]

        # broadcast single values to lists of len(identifier)
        (
            latitude,
            longitude,
            start_utc,
            end_utc,
            min_sim_period,
            step_size_minutes,
            min_chunk_period,
        ) = [
            [v] * len(identifier)
            if (not isinstance(v, Iterable) or isinstance(v, str))
            else v
            for v in [
                latitude,
                longitude,
                start_utc,
                end_utc,
                min_sim_period,
                step_size_minutes,
                min_chunk_period,
            ]
        ]

        # parse and validate input
        for i in range(len(identifier)):
            if not isinstance(latitude[i], float):
                raise ValueError(
                    f"latitude[{i}]: {latitude[i]} is not a float."
                )
            if not isinstance(longitude[i], float):
                raise ValueError(
                    f"longitude[{i}]: {longitude[i]} is not a float."
                )
            # convert str to datetime utc
            if isinstance(start_utc[i], str):
                start_utc[i] = pd.Timestamp(start_utc[i], tz="utc")
            if isinstance(end_utc[i], str):
                end_utc[i] = pd.Timestamp(end_utc[i], tz="utc")

            if not isinstance(start_utc[i], pd.Timestamp):
                raise ValueError(
                    f"start_utc[{i}]: {start_utc[i]} is not convertable to pd.Timestamp."
                )
            if not isinstance(end_utc[i], pd.Timestamp):
                raise ValueError(
                    f"end_utc[{i}]: {end_utc[i]} is not convertable to pd.Timestamp."
                )

            # convert str to timedelta
            if isinstance(min_sim_period[i], str):
                min_sim_period[i] = pd.Timedelta(min_sim_period[i])
            if isinstance(min_chunk_period[i], str):
                min_chunk_period[i] = pd.Timedelta(min_chunk_period[i])

            if not isinstance(min_sim_period[i], pd.Timedelta):
                raise ValueError(
                    f"min_sim_period[{i}]: {min_sim_period[i]} is not convertable to pd.Timedelta."
                )
            if not isinstance(min_chunk_period[i], pd.Timedelta):
                raise ValueError(
                    f"min_chunk_period[{i}]: {min_chunk_period[i]} is not convertable to pd.Timedelta."
                )

        _df = pd.DataFrame.from_dict(
            {
                "identifier": identifier,
                "latitude": latitude,
                "longitude": longitude,
                "start_utc": start_utc,
                "end_utc": end_utc,
                "min_sim_period": min_sim_period,
                "min_chunk_period": min_chunk_period,
                "step_size_minutes": step_size_minutes,
            }
        )

        return _df
