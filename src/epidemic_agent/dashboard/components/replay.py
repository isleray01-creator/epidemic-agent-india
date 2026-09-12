from __future__ import annotations

from typing import Any

import streamlit as st


def create_animation_controls(
    key_prefix: str = "anim",
    max_frames: int = 100,
) -> dict[str, Any]:
    col1, col2, col3, col4 = st.columns([2, 1, 1, 1])

    with col1:
        frame = st.slider(
            "Day",
            min_value=0,
            max_value=max_frames - 1,
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

    with col4:
        if st.button("↺ Reset", key=f"{key_prefix}_reset"):
            frame = 0
            playing = False

    return {
        "frame": frame,
        "playing": playing,
        "speed": speed,
    }


def create_state_selector(
    states: list[str],
    key_prefix: str = "state",
) -> str:
    options = ["All"] + sorted(states)
    return st.selectbox(
        "Select State",
        options,
        index=0,
        key=f"{key_prefix}_selector",
    )


def create_metric_selector(
    key_prefix: str = "metric",
) -> str:
    metrics = {
        "daily_cases": "Daily Cases",
        "daily_deaths": "Daily Deaths",
        "daily_Rt": "Rt (Reproduction Number)",
        "cumulative_cases": "Cumulative Cases",
        "cumulative_deaths": "Cumulative Deaths",
    }
    return st.selectbox(
        "Metric",
        list(metrics.values()),
        index=0,
        key=f"{key_prefix}_selector",
    )
