from __future__ import annotations

from typing import Any

import plotly.graph_objects as go


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

        fig.add_annotation(
            x=day,
            y=1.05,
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
        yaxis=dict(visible=False, range=[0, 1.2]),
        height=height,
        margin={"l": 50, "r": 50, "t": 50, "b": 50},
        showlegend=False,
    )

    return fig
