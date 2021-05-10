# created by Tom Stesco tom.s@ecobee.com

from abc import ABC, abstractmethod
from enum import IntEnum
import logging

import attr
import pandas as pd
import numpy as np

from BuildingControlsSimulator.ControllerModels.ControllerStatus import CONTROLLERSTATUS


@attr.s
class ControllerModel(ABC):
    """ABC for control models"""

    input_states = attr.ib()
    output_states = attr.ib()
    step_size_seconds = attr.ib()
    discretization_size_seconds = attr.ib()

    output = attr.ib(factory=dict)
    step_output = attr.ib(factory=dict)
    settings = attr.ib(factory=dict)

    current_t_idx = attr.ib(default=None)
    current_t_start = attr.ib(default=None)
    start_utc = attr.ib(default=None)

    init_status = attr.ib(factory=list)
    step_status = attr.ib(factory=list)
    log_level = attr.ib(default=0)

    @abstractmethod
    def initialize(self, start_utc, t_start, t_end, t_step, data_spec, categories_dict):
        """Run on first setup and not again."""
        pass

    @abstractmethod
    def do_step(self):
        """Defines sequence of step internals."""
        pass

    @abstractmethod
    def change_settings(self, new_settings):
        """Change persistent internal settings to model."""
        pass

    @abstractmethod
    def get_model_name(self):
        """Defines human readable uniquely identifing name"""
        pass

    def get_step_time_utc(self):
        """For debugging use"""
        return self.start_utc + pd.Timedelta(
            seconds=self.current_t_idx * self.step_size_seconds
        )

    def update_settings(
        self,
        change_points_schedule,
        change_points_comfort_prefs,
        change_points_hvac_mode,
        time_utc=None,
        init=False,
    ):
        """Ensure settings are correct for given time step."""

        _init_time_hvac_mode = min(change_points_hvac_mode.keys())

        _init_time_schedule = min(change_points_schedule.keys())

        _init_schedule_names = set(
            [sch["name"] for sch in change_points_schedule[_init_time_schedule]]
        )

        _init_time_setpoints = []
        for _name in _init_schedule_names:
            _schedule_change_times = [
                k for k, v in change_points_comfort_prefs.items() if _name in v.keys()
            ]
            if _schedule_change_times:
                _init_time_setpoints.append(min(_schedule_change_times))
            else:
                # TODO: can make some assumption about set points
                raise ValueError(
                    f"Setpoints could not be detected for: {_name} schedule."
                )

        if init:
            if not change_points_comfort_prefs:
                logging.error(
                    "change_points_comfort_prefs is empty. update_settings will not work."
                )

            if not change_points_schedule:
                logging.error(
                    "change_points_schedule is empty. update_settings will not work."
                )

            if not change_points_hvac_mode:
                logging.error(
                    "change_points_hvac_mode is empty. update_settings will not work."
                )

            self.settings = {}
            self.settings["hvac_mode"] = change_points_hvac_mode[_init_time_hvac_mode]
            self.settings["schedules"] = change_points_schedule[_init_time_schedule]

            # need to update setpoints per schedule
            self.settings["setpoints"] = {}
            for _name in _init_schedule_names:
                _schedule_change_times = [
                    k
                    for k, v in change_points_comfort_prefs.items()
                    if _name in v.keys()
                ]
                self.settings["setpoints"][_name] = change_points_comfort_prefs[
                    min(_schedule_change_times)
                ][_name]

        elif time_utc:
            settings_updated = False

            if (
                time_utc in change_points_hvac_mode.keys()
                and time_utc != _init_time_hvac_mode
            ):
                # check that this is not init time for hvac_mode
                self.settings["hvac_mode"] = change_points_hvac_mode[time_utc]
                settings_updated = True

            # must observe new schedule at or before setpoint change
            if (
                time_utc in change_points_schedule.keys()
                and time_utc != _init_time_schedule
            ):
                # check that this is not init time for setpoint
                self.settings["schedules"] = change_points_schedule[time_utc]
                settings_updated = True

            if (
                time_utc in change_points_comfort_prefs.keys()
                and time_utc not in _init_time_setpoints
            ):
                # do not need to reset all setpoints, store previous setpoints
                # even after schedule is removed because it may be readded
                # check that this is not init time for setpoint
                for k, v in change_points_comfort_prefs[time_utc].items():
                    # overwrite existing or make new setpoint comfort prefs
                    self.settings["setpoints"][k] = v

                settings_updated = True

            if settings_updated:
                self.change_settings(self.settings)
        else:
            raise ValueError(
                "Invalid arguments supplied to update_settings()"
                + "Neither time_utc or init flag given."
            )
