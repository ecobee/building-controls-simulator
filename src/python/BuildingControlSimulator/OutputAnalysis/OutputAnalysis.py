# created by Tom Stesco tom.s@ecobee.com

import os
import logging

import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
import plotly
import attr


logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s %(levelname)-8s %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)


@attr.s
class OutputAnalysis(object):
    """OutputAnalysis

    Example:
    ```python


    ``` 
    """

    df = attr.ib(default=None)

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

    def diagnostic_plot(self, show=False):
        """
        """
        fig = plotly.subplots.make_subplots(
            subplot_titles=("Thermal", "Power", "Control Signals"),
            rows=3,
            cols=1,
            shared_xaxes=True,
            x_title="Time",
            row_heights=[2, 1, 1],   # relative heights
            vertical_spacing=0.05,
            specs=[
                [
                    {"secondary_y": True},
                ],
                [
                    {"secondary_y": False},
                ],
                [
                    {"secondary_y": True},
                ],
            ],
        )

        self.thermal_plot(fig=fig, row=1, col=1)
        self.power_plot(fig=fig, row=2, col=1)
        self.control_actuation_plot(fig=fig, row=3, col=1)

        layout = go.Layout(
            title_text="Diagnostic Plots",
            autosize=False,
            width=1500,
            height=1000,
            hovermode='closest',
        )

        fig.update_layout(layout)

        if show:
            fig.show()
        


    def thermal_plot(self, fig, row, col):
        """
        """

        fig.update_yaxes(title_text="Temperature (°C)", row=row, col=col)

        # legend subtitle
        fig.add_trace(
            go.Scatter(x=self.df.datetime, y=np.zeros(len(self.df.datetime)), mode="lines", visible='legendonly', name="Thermal diagnostics"),
            row=row,
            col=col,
            secondary_y=False,
        )
        

        for c in [c for c in self.df.columns if "Zone_Air_Temperature" in c]:
            fig.add_trace(
                go.Scatter(x=self.df.datetime, y=self.df[c], mode="lines", name=c),
                row=1,
                col=1,
                secondary_y=False,
            )

        fig.add_trace(
            go.Scatter(
                x=self.df.datetime, y=self.df["t_ctrl"], mode="lines", name="T_ctrl"
            ),
            row=row,
            col=col,
            secondary_y=False,
        )

        for c in [
            c for c in self.df.columns if "Site_Outdoor_Air_Drybulb_Temperature" in c
        ]:
            fig.add_trace(
                go.Scatter(
                    x=self.df.datetime, y=self.df[c], mode="lines", name="T_outdoor"
                ),
                row=row,
                col=col,
                secondary_y=True,
            )

        fig.add_trace(
            go.Scatter(
                x=self.df.datetime,
                y=self.df["stp_heat"],
                mode="lines",
                line=dict(color="firebrick", width=1, dash="dash"),
                name="stp_heat",
            ),
            row=row,
            col=col,
            secondary_y=False,
        )
        fig.add_trace(
            go.Scatter(
                x=self.df.datetime,
                y=self.df["stp_heat"] + self.df["deadband"],
                mode="lines",
                name="stp_heat_upper",
            ),
            row=row,
            col=col,
            secondary_y=False,
        )
        fig.add_trace(
            go.Scatter(
                x=self.df.datetime,
                y=self.df["stp_heat"] - self.df["deadband"],
                mode="lines",
                name="stp_heat_lower",
            ),
            row=row,
            col=col,
            secondary_y=False,
        )

        fig.add_trace(
            go.Scatter(
                x=self.df.datetime,
                y=self.df["stp_cool"],
                mode="lines",
                line=dict(color="blue", width=1, dash="dash"),
                name="stp_cool",
            ),
            row=row,
            col=col,
            secondary_y=False,
        )
        fig.add_trace(
            go.Scatter(
                x=self.df.datetime,
                y=self.df["stp_cool"] + self.df["deadband"],
                mode="lines",
                name="stp_cool_upper",
            ),
            row=row,
            col=col,
            secondary_y=False,
        )
        fig.add_trace(
            go.Scatter(
                x=self.df.datetime,
                y=self.df["stp_cool"] - self.df["deadband"],
                mode="lines",
                name="stp_cool_lower",
            ),
            row=row,
            col=col,
            secondary_y=False,
        )


    def power_plot(self, fig, row, col):
        """
        """

        fig.update_yaxes(title_text="Power (W)", row=row, col=col)

        # legend subtitle
        fig.add_trace(
            go.Scatter(x=self.df.datetime, y=np.zeros(len(self.df.datetime)), mode="lines", visible='legendonly', name="Power diagnostics"),
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

    def control_actuation_plot(self, fig, row, col):
        # traces = []

        fig.update_yaxes(title_text="Signal", row=row, col=col)

        # legend subtitle
        fig.add_trace(
            go.Scatter(
                x=self.df.datetime,
                y=np.zeros(len(self.df.datetime)),
                mode="lines",
                visible='legendonly',
                name="Control signal diagnostics",
            ),
            row=row,
            col=col,
            secondary_y=False,
        )
        

        for c in [c for c in self.df.columns if "Setpoint_Temperature" in c]:
            fig.add_trace(
                go.Scatter(
                    x=self.df.datetime,
                    y=self.df[c],
                    mode="lines",
                    line_shape="hv",
                    name=c,
                ),
                row=row,
                col=col,
                secondary_y=True,
            )

        fig.add_trace(
            go.Scatter(
                x=self.df.datetime,
                y=self.df["HVAC_mode"],
                mode="lines",
                line_shape="hv",
                name="HVAC_mode",
                yaxis="y2",
            ),
            row=row,
            col=col,
        )
