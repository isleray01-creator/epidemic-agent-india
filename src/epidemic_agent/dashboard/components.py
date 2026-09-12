from __future__ import annotations

from typing import Any

import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from plotly.subplots import make_subplots

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

METRIC_LABELS = {
    "daily_cases": "Daily Cases",
    "daily_deaths": "Daily Deaths",
    "daily_Rt": "Rt (Reproduction Number)",
    "cumulative_cases": "Cumulative Cases",
    "cumulative_deaths": "Cumulative Deaths",
}


def _resolve_metric_key(label: str) -> str:
    for k, v in METRIC_LABELS.items():
        if v == label:
            return k
    return "daily_cases"


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


def create_animated_choropleth(
    results: dict[str, Any],
    states: list[str],
    metric_key: str = "daily_cases",
    metric_label: str = "Daily Cases",
) -> go.Figure:
    values_per_state = results.get(metric_key, {})
    if not values_per_state:
        fig = go.Figure()
        fig.add_annotation(text="No data available", x=0.5, y=0.5, showarrow=False)
        return fig

    n_days = max(len(v) for v in values_per_state.values()) if values_per_state else 0
    if n_days == 0:
        fig = go.Figure()
        fig.add_annotation(text="No data available", x=0.5, y=0.5, showarrow=False)
        return fig

    day0_data = {}
    for s in states:
        vals = values_per_state.get(s, [])
        day0_data[s] = vals[0] if vals else 0

    fig = go.Figure(
        data=[go.Choropleth(
            geojson=INDIA_GEOJSON_URL,
            locations=list(day0_data.keys()),
            featureidkey="properties.ST_NM",
            z=list(day0_data.values()),
            colorscale="Reds",
            colorbar_title=metric_label,
            hovertemplate="<b>%{location}</b><br>" + metric_label + ": %{z}<extra></extra>",
        )],
        frames=[
            go.Frame(
                data=[go.Choropleth(
                    geojson=INDIA_GEOJSON_URL,
                    locations=list(frame_data.keys()),
                    featureidkey="properties.ST_NM",
                    z=list(frame_data.values()),
                    colorscale="Reds",
                    colorbar_title=metric_label,
                    hovertemplate="<b>%{location}</b><br>" + metric_label + ": %{z}<extra></extra>",
                )],
                name=f"day_{day}",
                layout=go.Layout(title_text=f"Day {day + 1} — {metric_label}"),
            )
            for day in range(n_days)
            for frame_data in [{
                s: values_per_state.get(s, [0] * n_days)[day]
                for s in states
            }]
        ],
    )

    fig.update_geos(
        fitbounds="locations",
        visible=False,
        projection_type="mercator",
    )

    fig.update_layout(
        title=f"Day 1 — {metric_label}",
        height=600,
        margin={"r": 0, "t": 40, "l": 0, "b": 0},
        geo=dict(bgcolor="rgba(0,0,0,0)"),
        updatemenus=[{
            "type": "buttons",
            "showactive": False,
            "y": 0.02,
            "x": 0.02,
            "buttons": [
                {
                    "label": "▶ Play",
                    "method": "animate",
                    "args": [
                        None,
                        {"frame": {"duration": 500, "redraw": True}, "fromcurrent": True},
                    ],
                },
                {
                    "label": "⏸ Pause",
                    "method": "animate",
                    "args": [
                        [None],
                        {"frame": {"duration": 0, "redraw": False}, "mode": "immediate"},
                    ],
                },
            ],
        }],
        sliders=[{
            "active": 0,
            "yanchor": "top",
            "xanchor": "left",
            "currentvalue": {"prefix": "Day ", "font": {"size": 14}},
            "pad": {"b": 10, "t": 50},
            "len": 0.9,
            "x": 0.05,
            "y": 0,
            "steps": [
                {
                    "args": [[f"day_{day}"], {"frame": {"duration": 0, "redraw": True}, "mode": "immediate"}],
                    "label": str(day + 1),
                    "method": "animate",
                }
                for day in range(n_days)
            ],
        }],
    )

    return fig


def create_multi_metric_figure(
    simulation_results: dict[str, Any],
    states: list[str],
    metrics: list[str] = None,
    days: int = None,
) -> go.Figure:
    metrics = metrics or ["daily_cases", "daily_deaths"]
    states = states or list(simulation_results.get("daily_cases", {}).keys())

    fig = go.Figure()
    colors = ["#636EFA", "#EF553B", "#00CC96", "#AB63FA", "#FFA15A", "#19D3F3"]

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
                name=f"{state} — {METRIC_LABELS.get(metric, metric)}",
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


def create_rt_heatmap(
    results: dict[str, Any],
    states: list[str],
    days: int = None,
) -> go.Figure:
    rt_data = results.get("daily_Rt", {})
    if not rt_data:
        fig = go.Figure()
        fig.add_annotation(text="No Rt data available", x=0.5, y=0.5, showarrow=False)
        return fig

    z = []
    for state in states:
        values = rt_data.get(state, [])
        if days:
            values = values[:days]
        z.append(values)

    x_labels = [str(d + 1) for d in range(max(len(row) for row in z) if z else 0)]

    fig = go.Figure(data=go.Heatmap(
        z=z,
        x=x_labels,
        y=states,
        colorscale="RdYlGn_r",
        colorbar_title="Rt",
        hovertemplate="State: %{y}<br>Day: %{x}<br>Rt: %{z:.2f}<extra></extra>",
        zmin=0,
        zmax=4,
    ))

    fig.update_layout(
        title="Reproduction Number (Rt) by State",
        xaxis_title="Day",
        yaxis_title="State",
        height=max(300, 60 * len(states)),
        margin={"l": 120, "r": 0, "t": 40, "b": 40},
    )

    return fig


def create_deaths_cases_dual_axis(
    results: dict[str, Any],
    states: list[str],
    days: int = None,
) -> go.Figure:
    fig = make_subplots(specs=[[{"secondary_y": True}]])

    colors_cases = ["#636EFA", "#EF553B", "#00CC96", "#AB63FA"]
    colors_deaths = ["#1F77B4", "#D62728", "#2CA02C", "#9467BD"]

    for i, state in enumerate(states):
        cases = results.get("cumulative_cases", {}).get(state, [])
        deaths = results.get("cumulative_deaths", {}).get(state, [])
        if days:
            cases = cases[:days]
            deaths = deaths[:days]
        x = list(range(1, len(cases) + 1))

        fig.add_trace(
            go.Bar(
                x=x, y=cases, name=f"{state} — Cases",
                marker_color=colors_cases[i % len(colors_cases)],
                opacity=0.7,
            ),
            secondary_y=False,
        )
        fig.add_trace(
            go.Scatter(
                x=x, y=deaths, name=f"{state} — Deaths",
                line=dict(color=colors_deaths[i % len(colors_deaths)], width=2),
            ),
            secondary_y=True,
        )

    fig.update_layout(
        title="Cumulative Cases (bars) vs Deaths (line)",
        xaxis_title="Day",
        height=500,
        hovermode="x unified",
        legend=dict(groupclick="toggleitem"),
    )
    fig.update_yaxes(title_text="Cumulative Cases", secondary_y=False)
    fig.update_yaxes(title_text="Cumulative Deaths", secondary_y=True)

    return fig


def create_intervention_timeline(
    intervention_history: list[dict[str, Any]],
    simulation_days: int,
    height: int = 200,
) -> go.Figure:
    fig = go.Figure()

    if not intervention_history:
        fig.add_annotation(text="No interventions recorded", x=0.5, y=0.5, showarrow=False)
        fig.update_layout(height=height, title="Intervention Timeline")
        return fig

    colors = {
        "contact_tracing": "#1f77b4",
        "lockdown": "#d62728",
        "mask_mandate": "#2ca02c",
        "vaccination_drive": "#ff7f0e",
        "enhanced_testing": "#9467bd",
        "travel_restriction": "#8c564b",
        "school_closure": "#e377c2",
    }

    for i, record in enumerate(intervention_history):
        day = record.get("day", 0)
        intervention = record.get("intervention_type", "unknown")
        cost = record.get("cost", 0)
        color = colors.get(intervention, "#7f7f7f")

        fig.add_shape(
            type="line",
            x0=day, x1=day,
            y0=0, y1=1,
            xref="x", yref="paper",
            line=dict(color=color, width=3, dash="dash"),
        )

        y_pos = 1.05 + (i % 3) * 0.12

        fig.add_annotation(
            x=day,
            y=y_pos,
            text=f"{intervention}<br>₹{cost:,.0f}",
            showarrow=True,
            arrowhead=2,
            arrowcolor=color,
            bgcolor=color,
            font=dict(color="white", size=10),
            yref="paper",
        )

    fig.update_layout(
        title="Intervention Timeline",
        xaxis=dict(range=[0, simulation_days], title="Day"),
        yaxis=dict(visible=False, range=[0, 1.5]),
        height=max(height, 250),
        margin={"l": 50, "r": 50, "t": 50, "b": 50},
        showlegend=False,
    )

    return fig


def create_animation_controls(
    key_prefix: str = "anim",
    max_frames: int = 100,
) -> dict[str, Any]:
    col1, col2, col3 = st.columns([3, 1, 1])

    with col1:
        frame = st.slider(
            "Day",
            min_value=0,
            max_value=max(max_frames - 1, 0),
            value=0,
            key=f"{key_prefix}_slider",
            label_visibility="collapsed",
        )

    with col2:
        playing = st.toggle(
            "▶ Play",
            value=False,
            key=f"{key_prefix}_play",
        )

    with col3:
        speed = st.select_slider(
            "Speed",
            options=[0.5, 1, 2, 5, 10],
            value=1,
            key=f"{key_prefix}_speed",
        )

    return {"frame": frame, "playing": playing, "speed": speed}


def create_state_selector(
    states: list[str],
    key_prefix: str = "state",
) -> str:
    options = ["All"] + sorted(states)
    return st.selectbox(
        "Select State",
        options,
        index=0,
        key=f"{key_prefix}_state_selector",
    )


def create_metric_selector(
    key_prefix: str = "metric",
) -> str:
    return st.selectbox(
        "Metric",
        list(METRIC_LABELS.values()),
        index=0,
        key=f"{key_prefix}_metric_selector",
    )
