# created by Tom Stesco tom.s@ecobee.com

import logging

import attr
import pandas as pd
import numpy as np

from BuildingControlsSimulator.DataClients.DataChannel import DataChannel
from BuildingControlsSimulator.DataClients.DataStates import STATES

logger = logging.getLogger(__name__)


@attr.s(kw_only=True)
class HVACChannel(DataChannel):
    _placeholder = attr.ib(default=None)

    @staticmethod
    def get_settings_change_points(data, step_size_minutes):
        """get all periods of:
        - schedules
        - comfort preferences
        """
        # schedule
        data["prev_schedule"] = data[STATES.SCHEDULE].shift(1)
        data["diff"] = data[STATES.DATE_TIME].diff()

        _schedule_chg = data[
            (data["prev_schedule"] != data[STATES.SCHEDULE])
            & (~data["prev_schedule"].isnull())
            & (data["diff"] == pd.Timedelta(minutes=step_size_minutes))
        ][[STATES.DATE_TIME, STATES.SCHEDULE]]

        _schedule_chg["dayofweek"] = _schedule_chg[
            STATES.DATE_TIME
        ].dt.dayofweek
        _schedule_chg["minuteofday"] = (
            _schedule_chg[STATES.DATE_TIME].dt.hour * 60
            + _schedule_chg[STATES.DATE_TIME].dt.minute
        )

        _schedule_modes = (
            _schedule_chg.groupby(
                [STATES.SCHEDULE, "dayofweek", "minuteofday"]
            )
            .agg({STATES.DATE_TIME: ["min", "max"]})
            .reset_index()
        )
        _schedule_modes = _schedule_chg_pts[
            ~_schedule_chg_pts[STATES.DATE_TIME]["min"].isnull()
        ].reset_index(drop=True)

        _schedule_chg_pts = 

        # TODO: resolve changes back to previous schedule

        # query schedule
        # t = pd.Timestamp("2018-06-05 15:00:00+00:00", tz="utc")
        # _schedule = _schedule_chg_pts.iloc[
        #     _schedule_chg_pts[
        #         (_schedule_chg_pts["dayofweek"] == t.dayofweek)
        #         & (_schedule_chg_pts[STATES.DATE_TIME]["min"] <= t)
        #         & (_schedule_chg_pts[STATES.DATE_TIME]["max"] >= t)
        #         & (_schedule_chg_pts["minuteofday"] <= t.hour * 60 + t.minute)
        #     ]["minuteofday"].idxmax()
        # ][STATES.SCHEDULE].values[0]

        # comfort preferences
        data["prev_stp_cool"] = data[STATES.TEMPERATURE_STP_COOL].shift(1)
        data["prev_stp_heat"] = data[STATES.TEMPERATURE_STP_HEAT].shift(1)
        data["prev_event"] = data[STATES.CALENDAR_EVENT].shift(1)
        data["next_event"] = data[STATES.CALENDAR_EVENT].shift(-1)
        # data["prev_schedule"] = data[STATES.SCHEDULE].shift(1)
        # data["next_schedule"] = data[STATES.SCHEDULE].shift(-1)
        breakpoint()
        _comfort_chg_pts = data[
            (data[STATES.CALENDAR_EVENT].isnull())
            & (data["prev_event"].isnull())
            & (data["next_event"].isnull())
            & (data["prev_schedule"] == data[STATES.SCHEDULE])
            & (data["next_schedule"] == data[STATES.SCHEDULE])
            & (
                (
                    (
                        data["prev_stp_cool"]
                        != data[STATES.TEMPERATURE_STP_COOL]
                    )
                    & (~data["prev_stp_cool"].isnull())
                    & (~data[STATES.TEMPERATURE_STP_COOL].isnull())
                )
                | (
                    (
                        data["prev_stp_heat"]
                        != data[STATES.TEMPERATURE_STP_HEAT]
                    )
                    & (~data["prev_stp_heat"].isnull())
                    & (~data[STATES.TEMPERATURE_STP_HEAT].isnull())
                )
            )
            & (data["diff"] == pd.Timedelta(minutes=step_size_minutes))
        ][
            [
                STATES.DATE_TIME,
                STATES.SCHEDULE,
                STATES.TEMPERATURE_STP_COOL,
                STATES.TEMPERATURE_STP_HEAT,
            ]
        ]

        _comfort_modes = (
            data[
                (data[STATES.CALENDAR_EVENT].isnull())
                & (data["prev_event"].isnull())
                & (data["next_event"].isnull())
                & (data["prev_schedule"] == data[STATES.SCHEDULE])
                & (data["next_schedule"] == data[STATES.SCHEDULE])
                & (~data[STATES.TEMPERATURE_STP_COOL].isnull())
                & (~data[STATES.TEMPERATURE_STP_HEAT].isnull())
                & (data["diff"] == pd.Timedelta(minutes=step_size_minutes))
            ][
                [
                    STATES.DATE_TIME,
                    STATES.SCHEDULE,
                    STATES.TEMPERATURE_STP_COOL,
                    STATES.TEMPERATURE_STP_HEAT,
                ]
            ]
            .groupby(
                [
                    STATES.SCHEDULE,
                    STATES.TEMPERATURE_STP_COOL,
                    STATES.TEMPERATURE_STP_HEAT,
                ]
            )
            .agg({STATES.DATE_TIME: ["min", "max"]})
            .reset_index()
        )

        _comfort_modes = _comfort_chg_pts[
            ~_comfort_chg_pts[STATES.DATE_TIME]["min"].isnull()
        ].reset_index(drop=True)
        # idx=
        # data[idx-5:idx+5]

        # resolve change back to previous set points
        for _schedule in _comfort_chg_pts[STATES.SCHEDULE].unique():
            

        # clean up columns
        data = data.drop(
            axis="columns",
            columns=[
                "diff",
                "prev_schedule",
                "prev_stp_cool",
                "prev_stp_heat",
            ],
        )
        pass
