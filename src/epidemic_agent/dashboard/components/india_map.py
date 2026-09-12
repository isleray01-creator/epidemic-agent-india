from __future__ import annotations

from typing import Any

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

INDIA_GEOJSON_URL = "https://gist.githubusercontent.com/jbrobst/56c13bbbf9d97d187fea01b62dc4c1ca/raw/629c14b6f5c7e8f5b4c5e8c7f5c2e8d1b4f8e9e8/india_states.geojson"

STATE_NAME_MAP = {
    "Andhra Pradesh": "Andhra Pradesh",
    "Arunachal Pradesh": "Arunachal Pradesh",
    "Assam": "Assam",
    "Bihar": "Bihar",
    "Chhattisgarh": "Chhattisgarh",
    "Goa": "Goa",
    "Gujarat": "Gujarat",
    "Haryana": "Haryana",
    "Himachal Pradesh": "Himachal Pradesh",
    "Jharkhand": "Jharkhand",
    "Karnataka": "Karnataka",
    "Kerala": "Kerala",
    "Madhya Pradesh": "Madhya Pradesh",
    "Maharashtra": "Maharashtra",
    "Manipur": "Manipur",
    "Meghalaya": "Meghalaya",
    "Mizoram": "Mizoram",
    "Nagaland": "Nagaland",
    "Odisha": "Odisha",
    "Punjab": "Punjab",
    "Rajasthan": "Rajasthan",
    "Sikkim": "Sikkim",
    "Tamil Nadu": "Tamil Nadu",
    "Telangana": "Telangana",
    "Tripura": "Tripura",
    "Uttar Pradesh": "Uttar Pradesh",
    "Uttarakhand": "Uttarakhand",
    "West Bengal": "West Bengal",
    "Andaman and Nicobar Islands": "Andaman and Nicobar Islands",
    "Chandigarh": "Chandigarh",
    "Dadra and Nagar Haveli and Daman and Diu": "Dadra and Nagar Haveli and Daman and Diu",
    "Delhi": "Delhi",
    "Jammu and Kashmir": "Jammu and Kashmir",
    "Ladakh": "Ladakh",
    "Lakshadweep": "Lakshadweep",
    "Puducherry": "Puducherry",
}


def create_india_choropleth(
    data: dict[str, float],
    metric_name: str = "Cases",
    colorscale: str = "Reds",
    title: str = "India Epidemic Map",
    height: int = 600,
) -> go.Figure:
    df = pd.DataFrame([
        {"state": k, "value": v}
        for k, v in data.items()
        if k in STATE_NAME_MAP
    ])

    if df.empty:
        fig = go.Figure()
        fig.add_annotation(text="No data available", x=0.5, y=0.5, showarrow=False)
        fig.update_layout(height=height, title=title)
        return fig

    fig = go.Figure(go.Choropleth(
        geojson=INDIA_GEOJSON_URL,
        locations=df["state"],
        featureidkey="properties.ST_NM",
        z=df["value"],
        colorscale=colorscale,
        colorbar_title=metric_name,
        hovertemplate="<b>%{location}</b><br>" + metric_name + ": %{z}<extra></extra>",
    ))

    fig.update_geos(
        fitbounds="locations",
        visible=False,
        projection_type="mercator",
    )

    fig.update_layout(
        title=title,
        height=height,
        margin={"r": 0, "t": 40, "l": 0, "b": 0},
        geo=dict(bgcolor="rgba(0,0,0,0)"),
    )

    return fig


def create_india_map_frames(
    simulation_results: dict[str, Any],
    metric: str = "daily_cases",
    max_frames: int = 100,
) -> list[dict[str, Any]]:
    frames = []
    states = simulation_results.get("daily_cases", {}).keys()

    if not states:
        return frames

    n_days = min(len(simulation_results["daily_cases"][list(states)[0]]), max_frames)

    for day in range(n_days):
        frame_data = {}
        for state in states:
            if metric in simulation_results and state in simulation_results[metric]:
                values = simulation_results[metric][state]
                if day < len(values):
                    frame_data[state] = values[day]
                else:
                    frame_data[state] = 0
            else:
                frame_data[state] = 0

        frames.append({
            "name": f"day_{day}",
            "data": [{
                "type": "choropleth",
                "locations": list(frame_data.keys()),
                "z": list(frame_data.values()),
                "geojson": INDIA_GEOJSON_URL,
                "featureidkey": "properties.ST_NM",
            }],
            "layout": {"title_text": f"Day {day + 1}"},
        })

    return frames


def create_multi_metric_figure(
    simulation_results: dict[str, Any],
    states: list[str],
    metrics: list[str] = None,
    days: int = None,
) -> go.Figure:
    metrics = metrics or ["daily_cases", "daily_deaths", "daily_Rt", "cumulative_cases"]
    states = states or list(simulation_results.get("daily_cases", {}).keys())

    fig = go.Figure()

    colors = px.colors.qualitative.Set1

    for i, state in enumerate(states):
        for j, metric in enumerate(metrics):
            if metric not in simulation_results:
                continue

            values = simulation_results[metric].get(state, [])
            if days:
                values = values[:days]

            x = list(range(1, len(values) + 1))
            fig.add_trace(go.Scatter(
                x=x,
                y=values,
                mode="lines",
                name=f"{state} - {metric}",
                line=dict(color=colors[i % len(colors)], dash="solid" if j < 2 else "dash"),
                visible=True if j == 0 else "legendonly",
            ))

    fig.update_layout(
        title="Epidemic Metrics Over Time",
        xaxis_title="Day",
        yaxis_title="Value",
        height=500,
        hovermode="x unified",
        legend=dict(groupclick="toggleitem"),
    )

    return fig
