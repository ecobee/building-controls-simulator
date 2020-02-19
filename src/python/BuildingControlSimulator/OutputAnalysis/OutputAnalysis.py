# created by Tom Stesco tom.s@ecobee.com

import os

import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
import plotly
import attr


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

    def thermal_plot(self, show=False):
        """
        """

        fig = plotly.subplots.make_subplots(
            rows=1, cols=1, specs=[[{"secondary_y": True}]]
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
            row=1,
            col=1,
            secondary_y=False,
        )

        for c in [
            c for c in self.df.columns if "Site_Outdoor_Air_Drybulb_Temperature" in c
        ]:
            fig.add_trace(
                go.Scatter(
                    x=self.df.datetime, y=self.df[c], mode="lines", name="T_outdoor"
                ),
                row=1,
                col=1,
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
            row=1,
            col=1,
            secondary_y=False,
        )
        fig.add_trace(
            go.Scatter(
                x=self.df.datetime,
                y=self.df["stp_heat"] + self.df["deadband"],
                mode="lines",
                name="stp_heat_upper",
            ),
            row=1,
            col=1,
            secondary_y=False,
        )
        fig.add_trace(
            go.Scatter(
                x=self.df.datetime,
                y=self.df["stp_heat"] - self.df["deadband"],
                mode="lines",
                name="stp_heat_lower",
            ),
            row=1,
            col=1,
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
            row=1,
            col=1,
            secondary_y=False,
        )
        fig.add_trace(
            go.Scatter(
                x=self.df.datetime,
                y=self.df["stp_cool"] + self.df["deadband"],
                mode="lines",
                name="stp_cool_upper",
            ),
            row=1,
            col=1,
            secondary_y=False,
        )
        fig.add_trace(
            go.Scatter(
                x=self.df.datetime,
                y=self.df["stp_cool"] - self.df["deadband"],
                mode="lines",
                name="stp_cool_lower",
            ),
            row=1,
            col=1,
            secondary_y=False,
        )

        fig.update_layout(title_text="Thermal Response")
        if show:
            fig.show()

    def power_plot(self, show=False):
        """
        """
        # TODO add equipment integration
        fig = plotly.subplots.make_subplots(rows=1, cols=1)
        fig.add_trace(
            go.Scatter(
                x=self.df.datetime,
                y=self.df["total_heating"],
                mode="lines",
                name="heating",
            ),
            row=1,
            col=1,
        )
        fig.add_trace(
            go.Scatter(
                x=self.df.datetime,
                y=self.df["total_cooling"],
                mode="lines",
                name="cooling",
            ),
            row=1,
            col=1,
        )
        fig.add_trace(
            go.Scatter(
                x=self.df.datetime,
                y=self.df["total_internal_gains"],
                mode="lines",
                name="internal_heat",
            ),
            row=1,
            col=1,
        )
        # fig.add_trace(go.Scatter(x=df.datetime, y=df["FMU_Main_Chiller_Chiller_Electric_Power"], mode='lines',name='chiller_power'), row=1, col=1)
        fig.update_layout(title_text="Power Response")
        if show:
            fig.show()

    def control_actuation_plot(self, show=False):
        traces = []
        for c in [c for c in self.df.columns if "Setpoint_Temperature" in c]:
            traces.append(
                go.Scatter(
                    x=self.df.datetime,
                    y=self.df[c],
                    mode="lines",
                    line_shape="hv",
                    name=c,
                )
            )

        traces.append(
            go.Scatter(
                x=self.df.datetime,
                y=self.df["HVAC_mode"],
                mode="lines",
                line_shape="hv",
                name="HVAC_mode",
                yaxis="y2",
            )
        )

        layout = go.Layout(
            title_text="Control Actuation",
            yaxis2=dict(range=[-2, 4], overlaying="y", side="right"),
        )

        fig = go.Figure(data=traces, layout=layout)
        if show:
            fig.show()
