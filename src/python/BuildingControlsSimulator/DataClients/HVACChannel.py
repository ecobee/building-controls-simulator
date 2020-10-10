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

    change_points_schedule = attr.ib()
    change_points_comfort_prefs = attr.ib()

    @staticmethod
    def extract_schedule_periods(chgs):
        periods = []
        for _idx, _chg in chgs.iterrows():
            _match_periods = [
                _period
                for _period in periods
                if (_period["name"] == _chg[STATES.SCHEDULE])
                and (_period["minute_of_day"] == _chg["minute_of_day"])
            ]
            if len(_match_periods) > 1:
                raise ValueError(
                    "Schedule invalid. Identical periods: "
                    + f"_match_periods={_match_periods}"
                )
            elif len(_match_periods) == 1:
                # check that day of week has been oberserved before
                # if not, assume part of same schedule and add it
                # if _match_periods[0]["on_day_of_week"][_chg["day_of_week"]] is True:
                #     return True
                if (
                    _match_periods[0]["on_day_of_week"][_chg["day_of_week"]]
                    is None
                ):
                    # observed period on new day of week
                    _match_periods[0]["on_day_of_week"][
                        _chg["day_of_week"]
                    ] = True
                elif (
                    _match_periods[0]["on_day_of_week"][_chg["day_of_week"]]
                    is False
                ):
                    raise ValueError(
                        "Schedule invalid. False values should not exist yet: "
                        + f"_chg={_chg}"
                    )
            elif len(_match_periods) == 0:
                # add new period
                _period = dict(
                    name=_chg[STATES.SCHEDULE],
                    minute_of_day=_chg["minute_of_day"],
                    on_day_of_week=[None] * 7,
                )

                _period["on_day_of_week"][_chg["day_of_week"]] = True
                periods.append(_period)

        return periods

    @staticmethod
    def get_next_week_schedule(schedule_chgs, dt):
        week_chgs = schedule_chgs[
            (schedule_chgs[STATES.DATE_TIME] >= dt)
            & (schedule_chgs[STATES.DATE_TIME] < dt + pd.Timedelta(days=7))
        ]
        periods = HVACChannel.extract_schedule_periods(week_chgs)

        # finally, change all on_day_of_week None to False
        # these periods were never observed
        for _period in periods:
            for _idx, _on_day_of_week in enumerate(_period["on_day_of_week"]):
                if _on_day_of_week is None:
                    _period["on_day_of_week"][_idx] = False

        return periods

    @staticmethod
    def get_schedule_change_points(data, step_size_minutes):

        # feature cols
        data["prev_schedule"] = data[STATES.SCHEDULE].shift(1)
        data["diff"] = data[STATES.DATE_TIME].diff()

        schedule_chgs = data[
            (data["prev_schedule"] != data[STATES.SCHEDULE])
            & (~data[STATES.SCHEDULE].isnull())
            & (~data["prev_schedule"].isnull())
            & (data["diff"] == pd.Timedelta(minutes=step_size_minutes))
        ][[STATES.DATE_TIME, STATES.SCHEDULE]]

        # drop feature columns after use
        data = data.drop(axis="columns", columns=["prev_schedule", "diff"])

        schedule_chgs["day_of_week"] = schedule_chgs[
            STATES.DATE_TIME
        ].dt.dayofweek
        schedule_chgs["minute_of_day"] = (
            schedule_chgs[STATES.DATE_TIME].dt.hour * 60
            + schedule_chgs[STATES.DATE_TIME].dt.minute
        )
        # iterate over schedule changes and determine dynamically if each is
        # a new
        pt_start = schedule_chgs[STATES.DATE_TIME].min()
        pt_end = schedule_chgs[STATES.DATE_TIME].max()
        # get first week schedule
        schedule_chg_pts = {
            pt_start: HVACChannel.get_next_week_schedule(
                schedule_chgs, pt_start
            )
        }
        # initialize first week of schedule changes as current schedule
        cur_schedule_week_chgs = schedule_chgs[
            (schedule_chgs[STATES.DATE_TIME] >= pt_start)
            & (
                schedule_chgs[STATES.DATE_TIME]
                < pt_start + pd.Timedelta(days=7)
            )
        ].sort_values(["day_of_week", "minute_of_day"])

        # check each week's schedule changes against last week for added or removed
        # periods
        _week_start = pt_start

        while _week_start <= pt_end:
            new_week = True
            week_chgs = schedule_chgs[
                (schedule_chgs[STATES.DATE_TIME] >= _week_start)
                & (
                    schedule_chgs[STATES.DATE_TIME]
                    < _week_start + pd.Timedelta(days=7)
                )
            ].sort_values(["day_of_week", "minute_of_day"])

            suffix_last = "_last"
            suffix_curr = "_curr"
            merged = cur_schedule_week_chgs.merge(
                week_chgs,
                on=[STATES.SCHEDULE, "day_of_week", "minute_of_day"],
                how="outer",
                suffixes=(suffix_last, suffix_curr),
                indicator=True,
            )

            # added change points are unambiguous because we have the record
            # where they occur
            added_chg_time = merged[merged["_merge"] == "right_only"][
                str(int(STATES.DATE_TIME)) + suffix_curr
            ].min()

            if added_chg_time is not pd.NaT:
                # have record of added change
                # add change point in schedule
                schedule_chg_pts[
                    added_chg_time
                ] = HVACChannel.get_next_week_schedule(
                    schedule_chgs, added_chg_time
                )
                # set cur_schedule_week_chgs to new schedule
                cur_schedule_week_chgs = schedule_chgs[
                    (schedule_chgs[STATES.DATE_TIME] >= added_chg_time)
                    & (
                        schedule_chgs[STATES.DATE_TIME]
                        < added_chg_time + pd.Timedelta(days=7)
                    )
                ].sort_values(["day_of_week", "minute_of_day"])
                # start new week at current chg_time
                _week_start = added_chg_time
                new_week = False
            else:
                # for the missing change points we need to find the time at which
                # they may be actually missing and check them until once is found
                for _idx, _missing_chg in merged[
                    merged["_merge"] == "left_only"
                ].iterrows():
                    # check if missing due to a missing data
                    _calendar_week_start = _week_start - pd.Timedelta(
                        days=_week_start.dayofweek,
                        hours=_week_start.hour,
                        minutes=_week_start.minute,
                    )

                    week_wrap = 0
                    if (
                        _missing_chg["day_of_week"] * 1440
                        + _missing_chg["minute_of_day"]
                    ) < (
                        _week_start.dayofweek * 1440
                        + _week_start.hour * 60
                        + _week_start.minute
                    ):
                        # missing change is in wrapped portion of week schedule
                        week_wrap = 1

                    _chg_time = _calendar_week_start + pd.Timedelta(
                        days=_missing_chg["day_of_week"] + week_wrap * 7,
                        minutes=_missing_chg["minute_of_day"],
                    )
                    _miss_rec = data[data[STATES.DATE_TIME] == _chg_time]
                    if not all(_miss_rec[STATES.SCHEDULE].isnull()):
                        # have record of missing change
                        # add change point in schedule
                        schedule_chg_pts[
                            _chg_time
                        ] = HVACChannel.get_next_week_schedule(
                            schedule_chgs, _chg_time
                        )
                        # set cur_schedule_week_chgs to new schedule
                        cur_schedule_week_chgs = schedule_chgs[
                            (schedule_chgs[STATES.DATE_TIME] >= _chg_time)
                            & (
                                schedule_chgs[STATES.DATE_TIME]
                                < _chg_time + pd.Timedelta(days=7)
                            )
                        ].sort_values(["day_of_week", "minute_of_day"])
                        # start new week at current chg_time
                        _week_start = _chg_time
                        new_week = False
                        # we can break out of the for loop on the first
                        # actually missing change because we will
                        # capture any additional changes when the week
                        # changes are extracted
                        break

            # if no added or missing changes then increment to next week
            if new_week:
                _week_start = _week_start + pd.Timedelta(days=7)

        return schedule_chg_pts

    @staticmethod
    def get_comfort_change_points(data, step_size_minutes):
        # comfort preferences
        data["prev_event"] = data[STATES.CALENDAR_EVENT].shift(1)
        data["next_event"] = data[STATES.CALENDAR_EVENT].shift(-1)
        data["prev_schedule"] = data[STATES.SCHEDULE].shift(1)
        data["next_schedule"] = data[STATES.SCHEDULE].shift(-1)

        filtered_df = data[
            # no overrides impacting setpoint during message interval
            (data[STATES.CALENDAR_EVENT].isnull())
            & (data["prev_event"].isnull())
            & (data["next_event"].isnull())
            # no schedule changes impacting setpoint during message interval
            & (~data[STATES.SCHEDULE].isnull())
            & (data["prev_schedule"] == data[STATES.SCHEDULE])
            & (data["next_schedule"] == data[STATES.SCHEDULE])
        ][
            [
                STATES.DATE_TIME,
                STATES.SCHEDULE,
                STATES.TEMPERATURE_STP_COOL,
                STATES.TEMPERATURE_STP_HEAT,
            ]
        ]

        # clean up columns
        data = data.drop(
            axis="columns",
            columns=[
                "prev_event",
                "next_event",
                "prev_schedule",
                "next_schedule",
            ],
        )

        comfort_chg_pts = {}
        # iterate over each schedule specifically and collect comfort changes
        for _schedule in filtered_df[STATES.SCHEDULE].cat.categories:
            schedule_spt_df = filtered_df[
                (filtered_df[STATES.SCHEDULE] == _schedule)
            ]
            schedule_spt_df["prev_stp_cool"] = schedule_spt_df[
                STATES.TEMPERATURE_STP_COOL
            ].shift(1)
            schedule_spt_df["prev_stp_heat"] = schedule_spt_df[
                STATES.TEMPERATURE_STP_HEAT
            ].shift(1)

            comfort_chgs = schedule_spt_df[
                (
                    (
                        schedule_spt_df["prev_stp_cool"]
                        != schedule_spt_df[STATES.TEMPERATURE_STP_COOL]
                    )
                    & (~schedule_spt_df["prev_stp_cool"].isnull())
                    & (~schedule_spt_df[STATES.TEMPERATURE_STP_COOL].isnull())
                )
                | (
                    (
                        schedule_spt_df["prev_stp_heat"]
                        != schedule_spt_df[STATES.TEMPERATURE_STP_HEAT]
                    )
                    & (~schedule_spt_df["prev_stp_heat"].isnull())
                    & (~schedule_spt_df[STATES.TEMPERATURE_STP_HEAT].isnull())
                )
            ]
            # store change points for schedule
            for _, _row in comfort_chgs.iterrows():
                comfort_chg_pts[
                    _row[STATES.DATE_TIME]
                ] = HVACChannel.extract_comfort_preferences(_row)

        return comfort_chg_pts

    @staticmethod
    def extract_comfort_preferences(comfort_chg_pt):
        return {
            comfort_chg_pt[STATES.SCHEDULE]: {
                STATES.TEMPERATURE_STP_COOL: comfort_chg_pt[
                    STATES.TEMPERATURE_STP_COOL
                ],
                STATES.TEMPERATURE_STP_HEAT: comfort_chg_pt[
                    STATES.TEMPERATURE_STP_HEAT
                ],
            },
        }

    @staticmethod
    def get_active_schedule(schedule_chg_pts, dt):
        first_chg_pt = list(schedule_chg_pts.keys())[0]
        if dt < first_chg_pt:
            # If times before first observed change point are needed default to
            # assuming time before first change point are equal because first change
            # point always extracts initial data.
            return schedule_chg_pts[first_chg_pt]

        for _dt, _schedule in schedule_chg_pts.items():
            if dt >= _dt:
                return _schedule

        return None

    @staticmethod
    def get_settings_change_points(data, step_size_minutes):
        """get setting change points:
        - schedules
        - comfort preferences

        The day of the week with Monday=0, Sunday=6.
        If times before first observed change point are needed default to
        assuming time before first change point are equal because first change
        point always extracts initial data.
        """

        data = data.sort_values(STATES.DATE_TIME).reset_index(drop=True)
        schedule_chg_pts = HVACChannel.get_schedule_change_points(
            data, step_size_minutes
        )
        comfort_chg_pts = HVACChannel.get_comfort_change_points(
            data, step_size_minutes
        )

        return schedule_chg_pts, comfort_chg_pts
