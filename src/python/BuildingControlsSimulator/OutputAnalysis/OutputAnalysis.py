# created by Tom Stesco tom.s@ecobee.com

import os
import logging
import textwrap

import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
import plotly
import plotly.figure_factory as ff

from BuildingControlsSimulator.DataClients.DataStates import STATES


class OutputAnalysis(object):
    """OutputAnalysis

    Example:
    ```python


    ```
    """

    def __init__(self, simulations, data_spec, humidity=False):
        self.data_spec = data_spec
        self.humidity = humidity

        self.n_simulations = len(simulations)
        self.sim_names = []
        self.time_zones = []
        self.input_data = []
        self.output_data = []
        self.controller_options = []
        self.controller_stage_cost = []

        for sim in simulations:
            _options = getattr(sim.controller_model, "options", None)
            if not _options:
                _controllers = getattr(sim.controller_model, "controllers", None)
                if _controllers:
                    _options = getattr(_controllers, "options", None)

            self.controller_options.append(_options)

            _stage_cost = getattr(sim.controller_model, "stage_cost", None)
            if not _stage_cost:
                _controllers = getattr(sim.controller_model, "controllers", None)
                if _controllers:
                    _stage_cost = getattr(_controllers, "stage_cost", None)

            self.controller_stage_cost.append(_stage_cost)

            self.sim_names.append(sim.sim_name)
            self.time_zones.append(sim.data_client.datetime.timezone)
            self.input_data.append(sim.full_input)
            self.output_data.append(sim.output)

    def postprocess(self):
        self.df["datetime"] = self.df["time_seconds"].apply(
            lambda t: pd.Timestamp("2019-01-01") + pd.Timedelta(seconds=t)
        )
        self.df["total_heating"] = self.df[
            [c for c in self.df.columns if "Air_System_Sensible_Heating_Rate" in c]
        ].sum(axis=1)
        self.df["total_cooling"] = self.df[
            [c for c in self.df.columns if "Air_System_Sensible_Cooling_Rate" in c]
        ].sum(axis=1)
        self.df["total_internal_gains"] = self.df[
            [
                c
                for c in self.df.columns
                if "Zone_Total_Internal_Total_Heating_Rate" in c
            ]
        ].sum(axis=1)

    def comparison_plot(self, show=False, actuals=True, local_time=True):
        """"""
        _titles = tuple(
            ["Solar", "Weather"]
            + sum(
                [
                    [
                        f"{_idx}: {'<br>'.join(textwrap.wrap(sim_name, 120))}<br>Thermal Response",
                        "Equipment Run-time",
                        # "Comfort",
                    ]
                    for _idx, sim_name in enumerate(self.sim_names)
                ],
                [],
            )
        )

        n_const_plots = 2
        n_var_plots = 2
        _rows = n_const_plots + n_var_plots * self.n_simulations
        _row_heights = [1] * n_const_plots + [1] * n_var_plots * self.n_simulations
        _specs = [[{"secondary_y": False},], [{"secondary_y": True},]] + [
            [
                {"secondary_y": True},
            ],
            [
                {"secondary_y": False},
            ],
            # [
            #     {"secondary_y": False},
            # ],
        ] * self.n_simulations

        fig = plotly.subplots.make_subplots(
            subplot_titles=_titles,
            rows=_rows,
            cols=1,
            shared_xaxes=True,
            x_title="Time",
            row_heights=_row_heights,  # relative heights
            # vertical_spacing=0.05,
            specs=_specs,
        )
        for _idx in range(self.n_simulations):

            if local_time:
                # need to copy if modifying time zone
                _output_data = self.output_data[_idx].copy(deep=True)
                _output_data[STATES.DATE_TIME] = _output_data[
                    STATES.DATE_TIME
                ].dt.tz_convert(self.time_zones[_idx])
                _input_data = self.input_data[_idx].copy(deep=True)
                _input_data[STATES.DATE_TIME] = _input_data[
                    STATES.DATE_TIME
                ].dt.tz_convert(self.time_zones[_idx])
            else:
                _output_data = self.output_data[_idx]
                _input_data = self.input_data[_idx]

            if _idx == 0:
                # solar and weather will be the same for all simulations
                self.solar_plot(
                    output_df=_output_data,
                    input_df=_input_data,
                    fig=fig,
                    row=1,
                    col=1,
                )

                self.weather_plot(
                    output_df=_output_data,
                    input_df=_input_data,
                    fig=fig,
                    row=2,
                    col=1,
                )

            row_idx = _idx * n_var_plots + (n_const_plots + 1)

            self.thermal_plot(
                output_df=_output_data,
                input_df=_input_data,
                idx=_idx,
                fig=fig,
                row=row_idx,
                col=1,
            )

            self.control_actuation_plot(
                output_df=_output_data,
                input_df=_input_data,
                idx=_idx,
                fig=fig,
                row=row_idx + 1,
                col=1,
            )

            # self.comfort_plot(
            #     output_df=_output_data,
            #     input_df=_input_data,
            #     idx=_idx,
            #     fig=fig,
            #     row=row_idx + 2,
            #     col=1,
            # )

        layout = go.Layout(
            title_text="Comparison Plots",
            autosize=False,
            width=1500,
            height=n_var_plots * self.n_simulations * 200 + n_const_plots * 200,
            hovermode="x unified",
        )

        fig.update_layout(layout)

        if show:
            fig.show()

    def performance_plot(self, show=False, actuals=True, local_time=True):
        """"""
        _titles = ["Cycle lengths"] * self.n_simulations
        _rows = 1 * self.n_simulations
        _row_heights = [2] * self.n_simulations
        _specs = [
            # [
            #     {"secondary_y": False},
            # ],
            [
                {"secondary_y": False},
            ],
        ] * self.n_simulations

        fig = plotly.subplots.make_subplots(
            subplot_titles=_titles,
            rows=_rows,
            cols=1,
            shared_xaxes=False,
            x_title="Time",
            row_heights=_row_heights,  # relative heights
            vertical_spacing=0.05,
            specs=_specs,
        )

        for _idx in range(self.n_simulations):

            if local_time:
                # need to copy if modifying time zone
                _output_data = self.output_data[_idx].copy(deep=True)
                _output_data[STATES.DATE_TIME] = _output_data[
                    STATES.DATE_TIME
                ].dt.tz_convert(self.time_zones[_idx])
                _input_data = self.input_data[_idx].copy(deep=True)
                _input_data[STATES.DATE_TIME] = _input_data[
                    STATES.DATE_TIME
                ].dt.tz_convert(self.time_zones[_idx])
            else:
                _output_data = self.output_data[_idx]
                _input_data = self.input_data[_idx]

            row_idx = _idx * 1 + 1

            self.cycle_plot(
                output_df=_output_data,
                input_df=_input_data,
                idx=_idx,
                fig=fig,
                row=row_idx,
                col=1,
            )

        layout = go.Layout(
            title_text="Performance Plots",
            autosize=False,
            width=1500,
            height=400,
            hovermode="x unified",
        )

        fig.update_layout(layout)

        if show:
            fig.show()

    def diagnostic_plot(self, show=False, actuals=True, local_time=True):
        """"""
        for _idx in range(self.n_simulations):

            if actuals:
                _titles = (
                    "Solar",
                    "Weather",
                    "Thermal Response",
                    "Equipment Run-time",
                    "Actual Thermal Response",
                    "Actual Equipment Run-time",
                )
                _row_heights = [1, 1, 1, 1, 1, 1]
                _specs = [
                    [
                        {"secondary_y": False},
                    ],
                    [
                        {"secondary_y": True},
                    ],
                    [
                        {"secondary_y": True},
                    ],
                    [
                        {"secondary_y": False},
                    ],
                    [
                        {"secondary_y": True},
                    ],
                    [
                        {"secondary_y": False},
                    ],
                ]
            else:
                _titles = ("Solar", "Weather", "Thermal Response", "Equipment Run-time")
                _row_heights = [1, 1, 1, 1]
                _specs = [
                    [
                        {"secondary_y": False},
                    ],
                    [
                        {"secondary_y": True},
                    ],
                    [
                        {"secondary_y": True},
                    ],
                    [
                        {"secondary_y": False},
                    ],
                ]

            _rows = len(_row_heights)

            fig = plotly.subplots.make_subplots(
                subplot_titles=_titles,
                rows=_rows,
                cols=1,
                shared_xaxes=True,
                x_title="Time",
                row_heights=_row_heights,  # relative heights
                vertical_spacing=0.05,
                specs=_specs,
            )

            self.solar_plot(
                output_df=self.output_data[_idx],
                input_df=self.input_data[_idx],
                fig=fig,
                row=1,
                col=1,
            )

            self.weather_plot(
                output_df=self.output_data[_idx],
                input_df=self.input_data[_idx],
                fig=fig,
                row=2,
                col=1,
            )

            self.thermal_plot(
                output_df=self.output_data[_idx],
                input_df=self.input_data[_idx],
                idx=_idx,
                fig=fig,
                row=3,
                col=1,
            )
            self.control_actuation_plot(
                output_df=self.output_data[_idx],
                input_df=self.input_data[_idx],
                idx=_idx,
                fig=fig,
                row=4,
                col=1,
            )

            if actuals:
                self.thermal_plot(
                    output_df=self.input_data[_idx],
                    input_df=self.input_data[_idx],
                    idx=_idx,
                    fig=fig,
                    row=5,
                    col=1,
                )
                self.control_actuation_plot(
                    output_df=self.input_data[_idx],
                    input_df=self.input_data[_idx],
                    idx=_idx,
                    fig=fig,
                    row=6,
                    col=1,
                )

            layout = go.Layout(
                title_text="Diagnostic Plots",
                autosize=False,
                width=1500,
                height=1000,
                hovermode="x unified",
            )

            fig.update_layout(layout)

            if show:
                fig.show()

    def solar_plot(self, output_df, input_df, fig, row, col):
        """"""
        fig.update_yaxes(title_text="Irradiance (W/m^2)", row=row, col=col)

        # legend subtitle
        fig.add_trace(
            go.Scatter(
                x=output_df[STATES.DATE_TIME],
                y=np.zeros(len(output_df[STATES.DATE_TIME])),
                mode="lines",
                visible="legendonly",
                name="Solar diagnostics",
            ),
            row=row,
            col=col,
        )

        fig.add_trace(
            go.Scatter(
                x=input_df[STATES.DATE_TIME],
                y=input_df[STATES.DIRECT_NORMAL_IRRADIANCE],
                mode="lines",
                name=self.data_spec.full.spec[STATES.DIRECT_NORMAL_IRRADIANCE]["name"],
                hoverlabel={"namelength": -1},
            ),
            row=row,
            col=col,
        )

        fig.add_trace(
            go.Scatter(
                x=input_df[STATES.DATE_TIME],
                y=input_df[STATES.GLOBAL_HORIZONTAL_IRRADIANCE],
                mode="lines",
                name=self.data_spec.full.spec[STATES.GLOBAL_HORIZONTAL_IRRADIANCE][
                    "name"
                ],
                hoverlabel={"namelength": -1},
            ),
            row=row,
            col=col,
        )

        fig.add_trace(
            go.Scatter(
                x=input_df[STATES.DATE_TIME],
                y=input_df[STATES.DIFFUSE_HORIZONTAL_IRRADIANCE],
                mode="lines",
                name=self.data_spec.full.spec[STATES.DIFFUSE_HORIZONTAL_IRRADIANCE][
                    "name"
                ],
                hoverlabel={"namelength": -1},
            ),
            row=row,
            col=col,
        )

    def weather_plot(self, output_df, input_df, fig, row, col):
        """"""
        fig.update_yaxes(title_text="Temperature (°C)", row=row, col=col)

        # legend subtitle
        fig.add_trace(
            go.Scatter(
                x=output_df[STATES.DATE_TIME],
                y=np.zeros(len(output_df[STATES.DATE_TIME])),
                mode="lines",
                visible="legendonly",
                name="Weather diagnostics",
            ),
            row=row,
            col=col,
            secondary_y=False,
        )

        fig.add_trace(
            go.Scatter(
                x=input_df[STATES.DATE_TIME],
                y=input_df[STATES.OUTDOOR_TEMPERATURE],
                mode="lines",
                name=self.data_spec.full.spec[STATES.OUTDOOR_TEMPERATURE]["name"],
                hoverlabel={"namelength": -1},
            ),
            row=row,
            col=col,
            secondary_y=False,
        )

        if self.humidity:
            fig.add_trace(
                go.Scatter(
                    x=input_df[STATES.DATE_TIME],
                    y=input_df[STATES.OUTDOOR_RELATIVE_HUMIDITY],
                    mode="lines",
                    name=self.data_spec.full.spec[STATES.OUTDOOR_RELATIVE_HUMIDITY][
                        "name"
                    ],
                    hoverlabel={"namelength": -1},
                ),
                row=row,
                col=col,
                secondary_y=True,
            )

    def thermal_plot(self, output_df, input_df, fig, row, col, idx):
        """"""
        fig.update_yaxes(title_text="Temperature (°C)", row=row, col=col)

        # legend subtitle
        fig.add_trace(
            go.Scatter(
                x=output_df[STATES.DATE_TIME],
                y=np.zeros(len(output_df[STATES.DATE_TIME])),
                mode="lines",
                visible="legendonly",
                name="Thermal diagnostics",
            ),
            row=row,
            col=col,
            secondary_y=False,
        )

        temperature_states = [
            STATES.TEMPERATURE_CTRL,
            # STATES.THERMOSTAT_TEMPERATURE,
            # STATES.RS1_TEMPERATURE,
            # STATES.RS2_TEMPERATURE,
        ]

        for c in [c for c in output_df.columns if c in temperature_states]:
            fig.add_trace(
                go.Scatter(
                    x=output_df[STATES.DATE_TIME],
                    y=output_df[c],
                    mode="lines",
                    name=self.data_spec.full.spec[c]["name"],
                    hoverlabel={"namelength": -1},
                ),
                row=row,
                col=col,
                secondary_y=False,
            )

        if self.humidity:
            fig.add_trace(
                go.Scatter(
                    x=output_df[STATES.DATE_TIME],
                    y=output_df[STATES.THERMOSTAT_HUMIDITY],
                    mode="lines",
                    line=dict(color="blue"),
                    name=self.data_spec.full.spec[STATES.THERMOSTAT_HUMIDITY]["name"],
                    hoverlabel={"namelength": -1},
                    visible="legendonly",
                ),
                row=row,
                col=col,
                secondary_y=True,
            )

        fig.add_trace(
            go.Scatter(
                x=output_df[STATES.DATE_TIME],
                y=output_df[STATES.TEMPERATURE_STP_HEAT],
                mode="lines",
                line=dict(color="firebrick", width=1, dash="dash"),
                name=self.data_spec.full.spec[STATES.TEMPERATURE_STP_HEAT]["name"],
                hoverlabel={"namelength": -1},
            ),
            row=row,
            col=col,
            secondary_y=False,
        )

        fig.add_trace(
            go.Scatter(
                x=output_df[STATES.DATE_TIME],
                y=output_df[STATES.TEMPERATURE_STP_HEAT]
                - self.controller_options[idx]["deadband"],
                mode="lines",
                line=dict(color="black", width=1, dash="dot"),
                name="deadband_min",
                hoverlabel={"namelength": -1},
            ),
            row=row,
            col=col,
            secondary_y=False,
        )

        # fig.add_trace(
        #     go.Scatter(
        #         x=output_df[STATES.DATE_TIME],
        #         y=output_df[STATES.TEMPERATURE_STP_COOL],
        #         mode="lines",
        #         line=dict(color="blue", width=1, dash="dash"),
        #         name=self.data_spec.full.spec[STATES.TEMPERATURE_STP_COOL]["name"],
        #         hoverlabel={"namelength": -1},
        #         visible="legendonly",
        #     ),
        #     row=row,
        #     col=col,
        #     secondary_y=False,
        # )

        # changes in calendar events
        if STATES.CALENDAR_EVENT in output_df.columns:
            chg_event = output_df[
                (
                    output_df[STATES.CALENDAR_EVENT]
                    != output_df[STATES.CALENDAR_EVENT].shift(1)
                )
                & ~(
                    (output_df[STATES.CALENDAR_EVENT].isnull())
                    & (output_df[STATES.CALENDAR_EVENT].shift(1).isnull())
                )
            ][
                [
                    STATES.DATE_TIME,
                    STATES.TEMPERATURE_STP_COOL,
                    STATES.CALENDAR_EVENT,
                ]
            ]
            fig.add_trace(
                go.Scatter(
                    x=chg_event[STATES.DATE_TIME],
                    y=chg_event[STATES.TEMPERATURE_STP_COOL] + 2.0,
                    mode="markers+text",
                    name=self.data_spec.full.spec[STATES.CALENDAR_EVENT]["name"],
                    text=chg_event[STATES.CALENDAR_EVENT],
                    textposition="bottom center",
                    hoverlabel={"namelength": -1},
                ),
                row=row,
                col=col,
                secondary_y=False,
            )

    def power_plot(self, fig, row, col, idx):
        """"""

        fig.update_yaxes(title_text="Power (W)", row=row, col=col)

        # legend subtitle
        fig.add_trace(
            go.Scatter(
                x=self.df.datetime,
                y=np.zeros(len(self.df.datetime)),
                mode="lines",
                visible="legendonly",
                name="Power diagnostics",
            ),
            row=row,
            col=col,
            secondary_y=False,
        )

        fig.add_trace(
            go.Scatter(
                x=self.df.datetime,
                y=self.df["total_heating"],
                mode="lines",
                name="heating",
            ),
            row=row,
            col=col,
            secondary_y=False,
        )
        fig.add_trace(
            go.Scatter(
                x=self.df.datetime,
                y=self.df["total_cooling"],
                mode="lines",
                name="cooling",
            ),
            row=row,
            col=col,
        )
        fig.add_trace(
            go.Scatter(
                x=self.df.datetime,
                y=self.df["total_internal_gains"],
                mode="lines",
                name="internal_heat",
            ),
            row=row,
            col=col,
        )

    def control_actuation_plot(self, output_df, input_df, fig, row, col, idx):
        fig.update_yaxes(title_text="Signal", row=row, col=col)

        # legend subtitle
        fig.add_trace(
            go.Scatter(
                x=output_df[STATES.DATE_TIME],
                y=np.zeros(len(output_df[STATES.DATE_TIME])),
                mode="lines",
                visible="legendonly",
                name="Control signal diagnostics",
            ),
            row=row,
            col=col,
            secondary_y=False,
        )

        hvac_states = [
            STATES.AUXHEAT1,
            # STATES.AUXHEAT2,
            # STATES.AUXHEAT3,
            # STATES.COMPCOOL1,
            # STATES.COMPCOOL2,
            # STATES.COMPHEAT1,
            # STATES.COMPHEAT2,
        ]

        for c in [c for c in output_df.columns if c in hvac_states]:
            fig.add_trace(
                go.Scatter(
                    x=output_df[STATES.DATE_TIME],
                    y=output_df[c],
                    mode="lines",
                    line_shape="vh",
                    name=self.data_spec.full.spec[c]["name"],
                    hoverlabel={"namelength": -1},
                ),
                row=row,
                col=col,
                secondary_y=False,
            )

    def comfort_plot(self, output_df, input_df, fig, row, col, idx):
        fig.update_yaxes(title_text="Comfort", row=row, col=col)

        comfort_df = self.get_comfort(
            output_df, input_df, controller_options=self.controller_options[idx]
        )

        fig.add_trace(
            go.Scatter(
                x=output_df[STATES.DATE_TIME],
                y=comfort_df,
                mode="lines",
                # line_shape="vh",
                name="comfort",
            ),
            row=row,
            col=col,
            secondary_y=False,
        )

    def get_comfort(self, output_df, input_df, controller_options):
        _comfort_df = pd.merge(
            output_df,
            input_df[
                [
                    STATES.DATE_TIME,
                    STATES.OUTDOOR_TEMPERATURE,
                    STATES.OUTDOOR_RELATIVE_HUMIDITY,
                ]
            ],
            on=STATES.DATE_TIME,
        )

        _comfort_df["comfort"] = _comfort_df[STATES.TEMPERATURE_CTRL] - (
            _comfort_df[STATES.TEMPERATURE_STP_HEAT] - controller_options["deadband"]
        )

        return _comfort_df["comfort"]

    def get_cycles(self, df, state):

        # for reference
        hvac_states = [
            STATES.AUXHEAT1,
            STATES.AUXHEAT2,
            STATES.AUXHEAT3,
            STATES.COMPCOOL1,
            STATES.COMPCOOL2,
            STATES.COMPHEAT1,
            STATES.COMPHEAT2,
        ]

        hvac_df = df[[state]].copy(deep=True)

        prev_state_1 = f"{str(state)}_prev_1"
        prev_state_2 = f"{str(state)}_prev_2"
        hvac_df[prev_state_1] = hvac_df[state].shift(periods=1)
        hvac_df[prev_state_2] = hvac_df[state].shift(periods=2)
        # hvac_df["COMPCOOL1_prev"] = hvac_df[STATES.COMPCOOL1].shift(periods=1)

        MIN_OFF_CYCLE = 300
        MIN_ON_CYCLE = 300

        hvac_df["cycle_on"] = 0
        hvac_df.loc[
            ((hvac_df[prev_state_1] == 0) & (hvac_df[state] > 0))
            | (
                (hvac_df[prev_state_1] + hvac_df[state] <= MIN_OFF_CYCLE)
                & (hvac_df[prev_state_2] + hvac_df[prev_state_1] >= MIN_ON_CYCLE)
                & (hvac_df[state] > 0)
            ),
            ["cycle_on"],
        ] = 1

        # | (
        #     (hvac_df["COMPCOOL1_prev"] == 0) & (hvac_df[STATES.COMPCOOL1] > 0)
        # )
        # | (
        #     (hvac_df["COMPCOOL1_prev"] + hvac_df[STATES.COMPCOOL1] <= MIN_OFF_CYCLE) & ( hvac_df[STATES.COMPCOOL1] > 0)
        # )

        # index each cycle
        hvac_df["cycle_id"] = hvac_df["cycle_on"].cumsum()
        # remove first cycle because it may be incomplete
        hvac_df = hvac_df[hvac_df["cycle_id"] > 0]
        # summing run time per cycle gives the duration of the on cycle
        cycles_df = (
            hvac_df[[state, "cycle_id"]]
            .groupby(["cycle_id"])
            .sum()
            .reset_index(drop=True)[state]
        )
        return cycles_df

    def performance_stats(self):
        metrics = [
            "total_run_time",
            "n_cycles",
            "cycle_length_min",
            "cycle_length_25%ile",
            "cycle_length_50%ile",
            "cycle_length_75%ile",
            "cycle_length_95%ile",
            "cycle_length_max",
            "comfort_min",
            "prob_discomfort",
        ]

        stats = {}
        for _idx in range(self.n_simulations):
            stats[_idx] = {}

            cycles_df = self.get_cycles(self.output_data[_idx], STATES.AUXHEAT1)
            comfort_df = self.get_comfort(
                self.output_data[_idx],
                self.input_data[_idx],
                controller_options=self.controller_options[_idx],
            )

            stats[_idx]["total_run_time"] = cycles_df.sum()
            stats[_idx]["n_cycles"] = cycles_df.count()
            stats[_idx]["cycle_length_min"] = cycles_df.min()
            stats[_idx]["cycle_length_25"] = cycles_df.quantile(0.25)
            stats[_idx]["cycle_length_50"] = cycles_df.quantile(0.50)
            stats[_idx]["cycle_length_75"] = cycles_df.quantile(0.75)
            stats[_idx]["cycle_length_95"] = cycles_df.quantile(0.95)
            stats[_idx]["cycle_length_max"] = cycles_df.max()

            stats[_idx]["comfort_min"] = comfort_df.min()
            stats[_idx]["prob_discomfort"] = len(comfort_df[comfort_df < 0.0]) / len(
                comfort_df
            )
            stats[_idx]["T_ctrl_mean"] = self.output_data[_idx][
                STATES.TEMPERATURE_CTRL
            ].mean()
            stats[_idx]["T_ctrl_min"] = self.output_data[_idx][
                STATES.TEMPERATURE_CTRL
            ].min()
            stats[_idx]["T_ctrl_05"] = self.output_data[_idx][
                STATES.TEMPERATURE_CTRL
            ].quantile(0.05)
            stats[_idx]["T_ctrl_25"] = self.output_data[_idx][
                STATES.TEMPERATURE_CTRL
            ].quantile(0.25)
            stats[_idx]["T_ctrl_50"] = self.output_data[_idx][
                STATES.TEMPERATURE_CTRL
            ].quantile(0.50)
            stats[_idx]["T_ctrl_75"] = self.output_data[_idx][
                STATES.TEMPERATURE_CTRL
            ].quantile(0.75)
            stats[_idx]["T_ctrl_95"] = self.output_data[_idx][
                STATES.TEMPERATURE_CTRL
            ].quantile(0.95)
            stats[_idx]["T_ctrl_max"] = self.output_data[_idx][
                STATES.TEMPERATURE_CTRL
            ].max()

        return pd.DataFrame.from_dict(stats)

    def cycle_plot(self, output_df, input_df, fig, row, col, idx):
        fig.update_yaxes(title_text="Cycle Lengths", row=row, col=col)

        cycles_df = self.get_cycles(output_df, STATES.AUXHEAT1)

        fig.add_trace(
            go.Histogram(
                x=cycles_df,
                name="cycle length",
                nbinsx=500,
                cumulative_enabled=True,
                histnorm="probability",
                marker={"opacity": 0.7, "line": {"color": "black"}},
            ),
            row=row,
            col=col,
            secondary_y=False,
        )
