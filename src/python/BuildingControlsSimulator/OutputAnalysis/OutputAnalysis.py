# created by Tom Stesco tom.s@ecobee.com

import os
import logging
import textwrap

import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
import plotly

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
        self.input_data = []
        self.output_data = []

        for sim in simulations:
            self.sim_names.append(sim.sim_name)
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
                        f"{'<br>'.join(textwrap.wrap(sim_name, 120))}<br>Thermal Response",
                        "Equipment Run-time",
                    ]
                    for sim_name in self.sim_names
                ],
                [],
            )
        )
        _rows = 2 * self.n_simulations + 2
        _row_heights = [1, 1] + [1, 1] * self.n_simulations
        _specs = [[{"secondary_y": False},], [{"secondary_y": True},]] + [
            [
                {"secondary_y": True},
            ],
            [
                {"secondary_y": False},
            ],
        ] * self.n_simulations

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

        # solar and weather will be the same for all simulations
        self.solar_plot(
            output_df=self.output_data[0],
            input_df=self.input_data[0],
            fig=fig,
            row=1,
            col=1,
        )

        self.weather_plot(
            output_df=self.output_data[0],
            input_df=self.input_data[0],
            fig=fig,
            row=2,
            col=1,
        )

        for _idx in range(self.n_simulations):
            row_idx = _idx * 2 + 3

            self.thermal_plot(
                output_df=self.output_data[_idx],
                input_df=self.input_data[_idx],
                fig=fig,
                row=row_idx,
                col=1,
            )
            self.control_actuation_plot(
                output_df=self.output_data[_idx],
                input_df=self.input_data[_idx],
                fig=fig,
                row=row_idx + 1,
                col=1,
            )

        # _min_date_time = _output_df[STATES.DATE_TIME].min()
        # _min_temperature = min(
        #     _output_df[STATES.THERMOSTAT_TEMPERATURE].min(),
        #     _input_df[STATES.OUTDOOR_TEMPERATURE].min()
        # )

        # fig.add_annotation(
        #     x=_min_date_time, y=_min_temperature,
        #     text=_simulation.sim_name,
        #     showarrow=False,
        #     yshift=10
        # )

        layout = go.Layout(
            title_text="Comparison Plots",
            autosize=False,
            width=1500,
            height=1000,
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
                fig=fig,
                row=3,
                col=1,
            )
            self.control_actuation_plot(
                output_df=self.output_data[_idx],
                input_df=self.input_data[_idx],
                fig=fig,
                row=4,
                col=1,
            )

            if actuals:
                self.thermal_plot(
                    output_df=self.input_data[_idx],
                    input_df=self.input_data[_idx],
                    fig=fig,
                    row=5,
                    col=1,
                )
                self.control_actuation_plot(
                    output_df=self.input_data[_idx],
                    input_df=self.input_data[_idx],
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
                    name=self.data_spec.full.spec[STATES.OUTDOOR_RELATIVE_HUMIDITY]["name"],
                    hoverlabel={"namelength": -1},
                ),
                row=row,
                col=col,
                secondary_y=True,
            )

    def thermal_plot(self, output_df, input_df, fig, row, col):
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
                y=output_df[STATES.TEMPERATURE_STP_COOL],
                mode="lines",
                line=dict(color="blue", width=1, dash="dash"),
                name=self.data_spec.full.spec[STATES.TEMPERATURE_STP_COOL]["name"],
                hoverlabel={"namelength": -1},
            ),
            row=row,
            col=col,
            secondary_y=False,
        )

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

    def power_plot(self, fig, row, col):
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

    def control_actuation_plot(self, output_df, input_df, fig, row, col):
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
            STATES.AUXHEAT2,
            STATES.AUXHEAT3,
            STATES.COMPCOOL1,
            STATES.COMPCOOL2,
            STATES.COMPHEAT1,
            STATES.COMPHEAT2,
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
