# created by Tom Stesco tom.s@ecobee.com
import logging
from pprint import pprint

import attr
import pandas as pd

from BuildingControlsSimulator.DataClients.DataChannel import DataChannel
from BuildingControlsSimulator.DataClients.DataStates import STATES

logger = logging.getLogger(__name__)


@attr.s(kw_only=True)
class ThermostatChannel(DataChannel):

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
        periods = ThermostatChannel.extract_schedule_periods(week_chgs)

        # finally, change all on_day_of_week None to False
        # these periods were never observed
        for _period in periods:
            for _idx, _on_day_of_week in enumerate(_period["on_day_of_week"]):
                if _on_day_of_week is None:
                    _period["on_day_of_week"][_idx] = False

        return periods

    @staticmethod
    def get_schedule_change_points(data, sim_step_size_seconds):
        # drop rows where schedule is missing so previous schedule is not null
        # and calculate diffs correctly
        if data.empty:
            schedule_chg_pts = {}
            return schedule_chg_pts

        schedule_data = data[[STATES.DATE_TIME, STATES.SCHEDULE]].dropna(
            subset=[STATES.SCHEDULE]
        )

        if schedule_data.empty:
            schedule_chg_pts = {}
            return schedule_chg_pts

        # feature cols
        schedule_data["prev_schedule"] = schedule_data[STATES.SCHEDULE].shift(
            1
        )
        schedule_data["diff"] = schedule_data[STATES.DATE_TIME].diff()

        schedule_chgs = schedule_data[
            (schedule_data["prev_schedule"] != schedule_data[STATES.SCHEDULE])
            & (~schedule_data[STATES.SCHEDULE].isnull())
            & (~schedule_data["prev_schedule"].isnull())
            & (
                schedule_data["diff"]
                == pd.Timedelta(seconds=sim_step_size_seconds)
            )
        ][[STATES.DATE_TIME, STATES.SCHEDULE]]

        if schedule_chgs.empty:
            # extract only schedule and return
            first_rec = schedule_data.iloc[0]
            schedule_chg_pts = {
                first_rec[STATES.DATE_TIME]: {
                    "name": first_rec[STATES.SCHEDULE],
                    "minute_of_day": 0,
                    "on_day_of_week": [True] * 7,
                }
            }
            return schedule_chg_pts

        schedule_chgs["day_of_week"] = schedule_chgs[
            STATES.DATE_TIME
        ].dt.dayofweek
        schedule_chgs["minute_of_day"] = (
            schedule_chgs[STATES.DATE_TIME].dt.hour * 60
            + schedule_chgs[STATES.DATE_TIME].dt.minute
        )

        # iterate over schedule changes and determine if each is new
        pt_start = schedule_chgs[STATES.DATE_TIME].min()
        pt_end = schedule_chgs[STATES.DATE_TIME].max()
        # get first week schedule
        schedule_chg_pts = {
            pt_start: ThermostatChannel.get_next_week_schedule(
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

        # check each week's schedule changes against last week for added or
        # removed periods
        _week_start = pt_start
        suffix_last = "_last"
        suffix_curr = "_curr"

        while _week_start <= pt_end:
            new_week = True
            week_chgs = schedule_chgs[
                (schedule_chgs[STATES.DATE_TIME] >= _week_start)
                & (
                    schedule_chgs[STATES.DATE_TIME]
                    < _week_start + pd.Timedelta(days=7)
                )
            ].sort_values(["day_of_week", "minute_of_day"])

            merged = cur_schedule_week_chgs.merge(
                week_chgs,
                on=["day_of_week", "minute_of_day"],
                how="outer",
                suffixes=(suffix_last, suffix_curr),
                indicator=True,
            ).sort_values([str(int(STATES.DATE_TIME)) + suffix_curr])

            # iterate through different changes between current schedule and
            # week's schedule changes
            for _idx, _chg in merged[merged["_merge"] != "both"].iterrows():

                _chg_time = _chg[str(int(STATES.DATE_TIME)) + suffix_curr]

                # changes that are not in previous schedule
                # case 1) previous week contained missing data at the time
                #    of change.
                #    If so add change to current schedule.
                # case 2) current week had missing data right before
                #    change, causing schedule change at wrong time.
                #    If so do nothing.
                # case 3) change last week contained different schedule
                #    and current schedule is not null.
                #    If so extract new schedule.
                if _chg["_merge"] == "right_only":
                    prev_week_chg_time = _chg_time - pd.Timedelta(days=7)
                    _prev_week_chg = schedule_data[
                        (schedule_data[STATES.DATE_TIME] == prev_week_chg_time)
                        & (
                            schedule_data[STATES.SCHEDULE]
                            != _chg[STATES.SCHEDULE]
                        )
                    ]
                    if _prev_week_chg.empty:
                        # case 1)
                        # revise previous schedule where data was missing
                        _revised_chg = pd.DataFrame.from_dict(
                            {
                                STATES.DATE_TIME: [_chg_time],
                                STATES.SCHEDULE: [_chg[STATES.SCHEDULE]],
                                "day_of_week": [_chg["day_of_week"]],
                                "minute_of_day": [_chg["minute_of_day"]],
                            },
                        )
                        # set index to above current index
                        # cur_schedule_week_chgs is only used for debugging
                        _revised_chg.index = [
                            cur_schedule_week_chgs.index.max() + 1
                        ]
                        cur_schedule_week_chgs = pd.concat(
                            [cur_schedule_week_chgs, _revised_chg]
                        ).sort_values(["day_of_week", "minute_of_day"])

                        # revise last schedule
                        schedule_chg_pts = (
                            ThermostatChannel.add_chg_to_last_schedule(
                                schedule_chg_pts, _chg
                            )
                        )

                    elif not _prev_week_chg.empty:
                        # case 2)
                        # check diff was over schedule change
                        # there would be a missing chg within the time period
                        _chg_diff = schedule_data[
                            (schedule_data[STATES.DATE_TIME] == _chg_time)
                        ]["diff"].iloc[0]
                        _before_chg_time = _chg_time - _chg_diff
                        _cur_min_of_week = (
                            _chg_time.dayofweek * 24 * 60
                            + _chg_time.hour * 60
                            + _chg_time.minute
                        )
                        _before_min_of_week = (
                            _before_chg_time.dayofweek * 24 * 60
                            + _before_chg_time.hour * 60
                            + _before_chg_time.minute
                        )

                        left_chgs = merged[
                            merged["_merge"] == "left_only"
                        ].copy(deep=True)
                        left_chgs["min_of_week"] = (
                            left_chgs["day_of_week"] * 24 * 60
                            + left_chgs["minute_of_day"]
                        )
                        unobserved_chgs = left_chgs[
                            (left_chgs["min_of_week"] > _before_min_of_week)
                            & (left_chgs["min_of_week"] < _cur_min_of_week)
                        ]

                        # check if any unobserved changes during missing data
                        # period are of the schedule that was missing and
                        # found in right when data started recording again
                        found_chg = unobserved_chgs[
                            unobserved_chgs[
                                str(int(STATES.SCHEDULE)) + suffix_last
                            ]
                            == _chg[str(int(STATES.SCHEDULE)) + suffix_curr]
                        ]
                        # if we found the missing change then do nothing

                        if found_chg.empty:
                            # case 3)
                            # add change point in schedule
                            schedule_chg_pts[
                                _chg_time
                            ] = ThermostatChannel.get_next_week_schedule(
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

                # changes that are in current schedule and missing
                # case 1) in period of missing data and assumed still active.
                #    If so do nothing.
                # case 2) existing data at time of change contained
                #    different schedule is not null.
                #    If so extract new schedule.
                elif _chg["_merge"] == "left_only":
                    # case 2)
                    # check if missing due to missing data
                    _calendar_week_start = _week_start - pd.Timedelta(
                        days=_week_start.dayofweek,
                        hours=_week_start.hour,
                        minutes=_week_start.minute,
                    )

                    week_wrap = 0
                    if (_chg["day_of_week"] * 1440 + _chg["minute_of_day"]) < (
                        _week_start.dayofweek * 1440
                        + _week_start.hour * 60
                        + _week_start.minute
                    ):
                        # missing change is in wrapped portion of week schedule
                        week_wrap = 1

                    _chg_time = _calendar_week_start + pd.Timedelta(
                        days=_chg["day_of_week"] + week_wrap * 7,
                        minutes=_chg["minute_of_day"],
                    )
                    # check for missing records
                    # and if they are not the expected schedule
                    _new_rec = schedule_data[
                        (schedule_data[STATES.DATE_TIME] == _chg_time)
                        & (
                            schedule_data[STATES.SCHEDULE]
                            != _chg[STATES.SCHEDULE]
                        )
                    ]

                    if not _new_rec.empty:
                        # have record of missing change
                        # add change point in schedule

                        _new_chg = _new_rec.iloc[0]
                        # check if missing due to missing data right before
                        if (
                            _new_chg[STATES.DATE_TIME] - _new_chg["diff"]
                            > _chg_time
                        ) or (
                            _new_chg[STATES.SCHEDULE]
                            == _new_chg["prev_schedule"]
                        ):
                            schedule_chg_pts[
                                _chg_time
                            ] = ThermostatChannel.get_next_week_schedule(
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
    def get_comfort_change_points(data, sim_step_size_seconds):
        if data.empty:
            return {}

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

        comfort_chg_pts = {}

        if filtered_df.empty:
            # check for all holds
            # use schedule column as check for record not being entirely null
            _hold_names = ["hold", "Hold", "auto", "HKhold"]
            if all(
                [
                    _cat
                    for _cat in data[~data[STATES.SCHEDULE].isnull()][
                        STATES.CALENDAR_EVENT
                    ].unique()
                    if _cat in _hold_names
                ]
            ):
                # entirely holds, set dummy comfort settings with mode
                for _schedule in data[STATES.SCHEDULE].cat.categories:
                    comfort_chg_pts[_schedule] = {
                        STATES.TEMPERATURE_STP_COOL: data[
                            STATES.TEMPERATURE_STP_COOL
                        ]
                        .mode()
                        .values[0],
                        STATES.TEMPERATURE_STP_HEAT: data[
                            STATES.TEMPERATURE_STP_HEAT
                        ]
                        .mode()
                        .values[0],
                    }
            else:
                # there is no unambiguous way to extract setpoints
                # TODO: do something less abrupt and log error.
                raise ValueError(
                    "There is no unambiguous way to extract setpoints."
                    + "Do not use this input data file for this time period."
                )

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

        # iterate over each schedule specifically and collect comfort changes
        for _schedule in filtered_df[STATES.SCHEDULE].cat.categories:
            schedule_spt_df = filtered_df[
                (filtered_df[STATES.SCHEDULE] == _schedule)
            ].reset_index(drop=True)

            if schedule_spt_df.empty:
                # while schedule may exist in full df it may have no occurance
                # in filtered df if the periods always occur with a hold
                # as well
                break

            schedule_spt_df["prev_stp_cool"] = schedule_spt_df[
                STATES.TEMPERATURE_STP_COOL
            ].shift(1)
            schedule_spt_df["prev_stp_heat"] = schedule_spt_df[
                STATES.TEMPERATURE_STP_HEAT
            ].shift(1)

            # extract initial setpoints for schedule
            _init_row = schedule_spt_df.iloc[0]
            comfort_chg_pts[
                _init_row[STATES.DATE_TIME]
            ] = ThermostatChannel.extract_comfort_preferences(_init_row)

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

            # store setpoint changes for schedule
            for _, _row in comfort_chgs.iterrows():
                comfort_chg_pts[
                    _row[STATES.DATE_TIME]
                ] = ThermostatChannel.extract_comfort_preferences(_row)

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
    def add_chg_to_last_schedule(schedule_chg_pts, chg):
        # check for existing period
        existing_period = False
        last_schedule = schedule_chg_pts[max(list(schedule_chg_pts.keys()))]
        for _period in last_schedule:
            if (_period["name"] == chg[STATES.SCHEDULE]) and (
                _period["minute_of_day"] == chg["minute_of_day"]
            ):
                # observed existing period on new day
                existing_period = True
                _period["on_day_of_week"][chg["day_of_week"]] = True

        if not existing_period:
            # add new period
            _new_chg = {
                "name": chg[STATES.SCHEDULE],
                "minute_of_day": chg["minute_of_day"],
                "on_day_of_week": [False] * 7,
            }
            _new_chg["on_day_of_week"][chg["day_of_week"]] = True
            schedule_chg_pts[max(list(schedule_chg_pts.keys()))].append(
                _new_chg
            )

        return schedule_chg_pts

    @staticmethod
    def get_active_schedule(schedule_chg_pts, dt):
        first_chg_pt = list(schedule_chg_pts.keys())[0]
        if dt < first_chg_pt:
            # If times before first observed change point are needed default to
            # assuming time before first change point are equal because first
            # change point always extracts initial data.
            return schedule_chg_pts[first_chg_pt]

        for _dt, _schedule in schedule_chg_pts.items():
            if dt >= _dt:
                return _schedule

        return None

    @staticmethod
    def get_settings_change_points(data, sim_step_size_seconds):
        """get setting change points:
        - schedules
        - comfort preferences

        The day of the week with Monday=0, Sunday=6.
        If times before first observed change point are needed default to
        assuming time before first change point are equal because first change
        point always extracts initial data.
        """

        data = data.sort_values(STATES.DATE_TIME).reset_index(drop=True)
        schedule_chg_pts = ThermostatChannel.get_schedule_change_points(
            data, sim_step_size_seconds
        )
        comfort_chg_pts = ThermostatChannel.get_comfort_change_points(
            data, sim_step_size_seconds
        )

        return schedule_chg_pts, comfort_chg_pts
