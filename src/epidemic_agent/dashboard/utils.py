from __future__ import annotations

from typing import Any

import streamlit as st


def format_number(n: float) -> str:
    if n >= 1e9:
        return f"{n/1e9:.2f}B"
    elif n >= 1e6:
        return f"{n/1e6:.2f}M"
    elif n >= 1e3:
        return f"{n/1e3:.2f}K"
    else:
        return f"{n:,.0f}"


def display_objective_breakdown(breakdown: dict[str, float]):
    cols = st.columns(len(breakdown))
    for i, (metric, value) in enumerate(breakdown.items()):
        with cols[i]:
            st.metric(
                metric.replace("_", " ").title(),
                f"{value:.4f}",
                help="Weight × normalized value"
            )


def create_download_button(
    data: Any,
    filename: str,
    label: str = "Download Data",
    mime: str = "application/json",
):
    import json
    if isinstance(data, (dict, list)):
        content = json.dumps(data, indent=2)
    else:
        content = str(data)

    st.download_button(
        label=label,
        data=content,
        file_name=filename,
        mime=mime,
    )
