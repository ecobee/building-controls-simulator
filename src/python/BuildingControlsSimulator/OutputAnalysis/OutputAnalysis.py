# created by Tom Stesco tom.s@ecobee.com

import os
import logging

import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
import plotly
import attr

from BuildingControlsSimulator.DataClients.DataStates import STATES
from BuildingControlsSimulator.DataClients.DataSpec import Internal


@attr.s
class OutputAnalysis(object):
    """OutputAnalysis

    Example:
    ```python


    ```
    """

    input_df = attr.ib()
    output_df = attr.ib()

    def postprocess(self):
        self.df["datetime"] = self.df["time_seconds"].apply(
            lambda t: pd.Timestamp("2019-01-01") + pd.Timedelta(seconds=t)
        )
        self.df["total_heating"] = self.df[
            [
                c
                for c in self.df.columns
                if "Air_System_Sensible_Heating_Rate" in c
            ]
        ].sum(axis=1)
        self.df["total_cooling"] = self.df[
            [
                c
                for c in self.df.columns
                if "Air_System_Sensible_Cooling_Rate" in c
            ]
        ].sum(axis=1)
        self.df["total_internal_gains"] = self.df[
            [
                c
                for c in self.df.columns
                if "Zone_Total_Internal_Total_Heating_Rate" in c
            ]
        ].sum(axis=1)

    def diagnostic_plot(self, show=False, actuals=True):
        """"""
        if actuals:
            _titles = (
                "Thermal Response",
                "Equipment Run-time",
                "Actual Thermal Response",
                "Actual Equipment Run-time",
            )
            _rows = 4
            _row_heights = [2, 1, 2, 1]
            _specs = [
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
            _titles = ("Thermal Response", "Equipment Run-time")
            _rows = 2
            _row_heights = [2, 1]
            _specs = [
                [
                    {"secondary_y": True},
                ],
                [
                    {"secondary_y": False},
                ],
            ]

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

        self.thermal_plot(
            output_df=self.output_df,
            input_df=self.input_df,
            fig=fig,
            row=1,
            col=1,
        )
        self.control_actuation_plot(
            output_df=self.output_df,
            input_df=self.input_df,
            fig=fig,
            row=2,
            col=1,
        )

        if actuals:
            self.thermal_plot(
                output_df=self.input_df,
                input_df=self.input_df,
                fig=fig,
                row=3,
                col=1,
            )
            self.control_actuation_plot(
                output_df=self.input_df,
                input_df=self.input_df,
                fig=fig,
                row=4,
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
            STATES.THERMOSTAT_TEMPERATURE,
            # STATES.RS1_TEMPERATURE,
            # STATES.RS2_TEMPERATURE,
        ]

        for c in [c for c in output_df.columns if c in temperature_states]:
            fig.add_trace(
                go.Scatter(
                    x=output_df[STATES.DATE_TIME],
                    y=output_df[c],
                    mode="lines",
                    name=Internal.full.spec[c]["name"],
                    hoverlabel={"namelength": -1},
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
                name=Internal.full.spec[STATES.OUTDOOR_TEMPERATURE]["name"],
                hoverlabel={"namelength": -1},
            ),
            row=row,
            col=col,
            secondary_y=True,
        )
        fig.add_trace(
            go.Scatter(
                x=input_df[STATES.DATE_TIME],
                y=input_df[STATES.TEMPERATURE_STP_HEAT],
                mode="lines",
                line=dict(color="firebrick", width=1, dash="dash"),
                name=Internal.full.spec[STATES.TEMPERATURE_STP_HEAT]["name"],
                hoverlabel={"namelength": -1},
            ),
            row=row,
            col=col,
            secondary_y=False,
        )

        fig.add_trace(
            go.Scatter(
                x=input_df[STATES.DATE_TIME],
                y=input_df[STATES.TEMPERATURE_STP_COOL],
                mode="lines",
                line=dict(color="blue", width=1, dash="dash"),
                name=Internal.full.spec[STATES.TEMPERATURE_STP_COOL]["name"],
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
                    name=Internal.full.spec[c]["name"],
                    hoverlabel={"namelength": -1},
                ),
                row=row,
                col=col,
                secondary_y=False,
            )
