from __future__ import annotations

import time
from typing import Any

import streamlit as st

from epidemic_agent.config import INDIA_STATES, VARIANT_PARAMS, settings
from epidemic_agent.graph import get_workflow
from epidemic_agent.persistence import get_state_store
from epidemic_agent.state import EpidemicState, SimulationConfig
from epidemic_agent.tools import fetch_epidemic_data

from .components import (
    create_animation_controls,
    create_india_choropleth,
    create_intervention_timeline,
    create_metric_selector,
    create_multi_metric_figure,
    create_state_selector,
)
from .utils import create_download_button, display_objective_breakdown, format_number

st.set_page_config(
    page_title="Epidemic Response Agent - India",
    page_icon="🦠",
    layout="wide",
    initial_sidebar_state="expanded",
)


@st.cache_data(ttl=3600)
def load_saved_simulation(filepath: str) -> dict[str, Any]:
    store = get_state_store()
    return store.load(filepath)


def initialize_session_state():
    if "workflow" not in st.session_state:
        st.session_state.workflow = get_workflow()

    if "simulation_state" not in st.session_state:
        st.session_state.simulation_state = None

    if "simulation_results" not in st.session_state:
        st.session_state.simulation_results = None

    if "current_recommendation" not in st.session_state:
        st.session_state.current_recommendation = None

    if "animation_frame" not in st.session_state:
        st.session_state.animation_frame = 0

    if "animation_playing" not in st.session_state:
        st.session_state.animation_playing = False


def create_initial_state(config: SimulationConfig) -> EpidemicState:
    population = {}
    for state in config.states:
        population[state] = settings.get_state_population(state)

    total_pop = sum(population.values())
    initial_infected_per_state = {
        s: int(config.initial_infected * population[s] / total_pop)
        for s in config.states
    }

    return EpidemicState(
        current_day=0,
        simulation_days=config.days,
        country=config.country,
        states=config.states,
        population=population,
        infected=initial_infected_per_state,
        exposed={s: v // 2 for s, v in initial_infected_per_state.items()},
        recovered=dict.fromkeys(config.states, 0),
        deceased=dict.fromkeys(config.states, 0),
        vaccinated={s: int(population[s] * 0.3) for s in config.states},
        active_variants=dict.fromkeys(config.states, config.initial_variant),
        variant_prevalence={s: {config.initial_variant: 1.0} for s in config.states},
        current_policies={s: [] for s in config.states},
        intervention_history=[],
        variant_shock=None,
        confidence_score=1.0,
        objective_value=0.0,
        objective_breakdown={},
        Rt_estimates=dict.fromkeys(config.states, VARIANT_PARAMS[config.initial_variant]["R0"]),
        healthcare_capacity={},
        contact_tracing_metrics={},
        metadata={"adaptation_loops": 0},
    )


def run_simulation_step(state: EpidemicState) -> EpidemicState:
    return st.session_state.workflow.run(state)


def render_sidebar():
    st.sidebar.title("🦠 Epidemic Response Agent")
    st.sidebar.markdown("---")

    tab = st.sidebar.radio(
        "Mode",
        ["New Simulation", "Load Saved", "Real-time Data"],
        key="mode_selector",
    )

    if tab == "New Simulation":
        render_new_simulation_sidebar()
    elif tab == "Load Saved":
        render_load_saved_sidebar()
    else:
        render_realtime_sidebar()


def render_new_simulation_sidebar():
    st.sidebar.subheader("Simulation Configuration")

    country = st.sidebar.selectbox("Country", ["India"], index=0)

    available_states = st.sidebar.multiselect(
        "States",
        INDIA_STATES,
        default=["Maharashtra", "Kerala", "Delhi", "Karnataka", "Tamil Nadu"],
        key="state_selector",
    )

    days = st.sidebar.slider("Simulation Days", 14, 180, 60, step=7)
    initial_infected = st.sidebar.number_input("Initial Infected", 10, 10000, 100)
    initial_variant = st.sidebar.selectbox(
        "Initial Variant",
        list(VARIANT_PARAMS.keys()),
        index=0,
    )

    interventions = st.sidebar.multiselect(
        "Interventions",
        ["contact_tracing", "lockdown", "mask_mandate", "vaccination_drive", "enhanced_testing"],
        default=["contact_tracing"],
    )

    if st.sidebar.button("🚀 Run Simulation", type="primary"):
        if not available_states:
            st.sidebar.error("Please select at least one state")
            return

        config = SimulationConfig(
            country=country,
            states=available_states,
            days=days,
            initial_infected=initial_infected,
            initial_variant=initial_variant,
            interventions=interventions,
        )

        initial_state = create_initial_state(config)
        with st.spinner("Running simulation..."):
            result = run_simulation_step(initial_state)

        st.session_state.simulation_state = result
        st.session_state.simulation_results = result["metadata"].get("predicted_outcomes", {})
        st.session_state.current_recommendation = result["metadata"].get("final_recommendation", {})
        st.success("Simulation complete!")


def render_load_saved_sidebar():
    st.sidebar.subheader("Load Saved State")
    store = get_state_store()
    saved_files = store.list_states()

    if not saved_files:
        st.sidebar.info("No saved states found")
        return

    selected = st.sidebar.selectbox("Select saved state", saved_files)

    if st.sidebar.button("Load"):
        try:
            state = load_saved_simulation(selected)
            st.session_state.simulation_state = state
            st.session_state.simulation_results = state["metadata"].get("predicted_outcomes", {})
            st.session_state.current_recommendation = state["metadata"].get("final_recommendation", {})
            st.success(f"Loaded {selected}")
        except Exception as e:
            st.error(f"Failed to load: {e}")


def render_realtime_sidebar():
    st.sidebar.subheader("Real-time Data Fetch")
    states = st.sidebar.multiselect(
        "States to fetch",
        INDIA_STATES,
        default=["Maharashtra", "Kerala", "Delhi"],
        key="realtime_states",
    )

    days_back = st.sidebar.slider("Days back", 7, 180, 30)

    if st.sidebar.button("Fetch Latest Data"):
        with st.spinner("Fetching data..."):
            result = fetch_epidemic_data.invoke({
                "states": states,
                "days_back": days_back,
            })
            st.session_state.realtime_data = result
            st.success("Data fetched!")


def render_dashboard():
    if st.session_state.simulation_state is None:
        render_welcome()
        return

    state = st.session_state.simulation_state
    results = st.session_state.simulation_results
    recommendation = st.session_state.current_recommendation

    render_header(state, recommendation)
    render_tabs(state, results, recommendation)


def render_welcome():
    st.title("🦠 Epidemic Response Agent - India")
    st.markdown("""
    Welcome to the **Epidemic Response Agent** for India. This agentic AI system:

    - **Monitors** real-time epidemic data from covid19india.org and CoWIN
    - **Simulates** disease spread using agent-based (Mesa) and compartmental (SEIR) models
    - **Adapts** to variant shocks through dynamic detection and re-planning
    - **Optimizes** interventions using a multi-objective function (deaths, economy, society, healthcare)
    - **Learns** variant parameters from observed epidemic waves

    **Get started:** Select "New Simulation" in the sidebar to configure and run a simulation.
    """)


def render_header(state: EpidemicState, recommendation: dict[str, Any]):
    col1, col2, col3, col4, col5 = st.columns(5)

    with col1:
        st.metric("Current Day", state["current_day"])
    with col2:
        total_infected = sum(state["infected"].values())
        st.metric("Active Cases", format_number(total_infected))
    with col3:
        total_deaths = sum(state["deceased"].values())
        st.metric("Total Deaths", format_number(total_deaths))
    with col4:
        st.metric("Objective", f"{state['objective_value']:.4f}")
    with col5:
        st.metric("Confidence", f"{state['confidence_score']:.2f}")

    if recommendation:
        st.info(f"**Recommendation:** {recommendation.get('rationale', 'No rationale available')}")


def render_tabs(state: EpidemicState, results: dict[str, Any], recommendation: dict[str, Any]):
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "🗺️ Map View",
        "📈 Metrics",
        "⏱️ Timeline",
        "🎬 Animation",
        "📋 Details",
    ])

    with tab1:
        render_map_tab(state, results)

    with tab2:
        render_metrics_tab(state, results)

    with tab3:
        render_timeline_tab(state, results)

    with tab4:
        render_animation_tab(state, results)

    with tab5:
        render_details_tab(state, results, recommendation)


def render_map_tab(state: EpidemicState, results: dict[str, Any]):
    st.subheader("Epidemic Map")

    col1, col2 = st.columns([3, 1])

    with col2:
        metric = create_metric_selector("map")
        metric_key = [k for k, v in {
            "daily_cases": "Daily Cases",
            "daily_deaths": "Daily Deaths",
            "daily_Rt": "Rt (Reproduction Number)",
            "cumulative_cases": "Cumulative Cases",
            "cumulative_deaths": "Cumulative Deaths",
        }.items() if v == metric][0]

        selected_state = create_state_selector(state["states"], "map")

    with col1:
        if results and metric_key in results:
            day_data = {}
            for s in state["states"]:
                values = results[metric_key].get(s, [])
                if values:
                    day_data[s] = values[-1]
                else:
                    day_data[s] = 0

            fig = create_india_choropleth(
                day_data,
                metric_name=metric,
                title=f"{metric} by State (Day {state['current_day']})",
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Run a simulation to see map data")


def render_metrics_tab(state: EpidemicState, results: dict[str, Any]):
    st.subheader("Epidemic Metrics Over Time")

    if not results:
        st.info("Run a simulation to see metrics")
        return

    selected_states = st.multiselect(
        "States to display",
        state["states"],
        default=state["states"][:3],
        key="metrics_states",
    )

    metrics = st.multiselect(
        "Metrics",
        ["daily_cases", "daily_deaths", "daily_Rt", "cumulative_cases", "cumulative_deaths"],
        default=["daily_cases", "daily_deaths", "daily_Rt"],
        key="metrics_list",
    )

    days = st.slider("Days to show", 7, state["simulation_days"], min(60, state["simulation_days"]))

    fig = create_multi_metric_figure(results, selected_states, metrics, days)
    st.plotly_chart(fig, use_container_width=True)

    st.subheader("Objective Breakdown")
    display_objective_breakdown(state["objective_breakdown"])


def render_timeline_tab(state: EpidemicState, results: dict[str, Any]):
    st.subheader("Intervention Timeline")

    fig = create_intervention_timeline(
        state["intervention_history"],
        state["simulation_days"],
    )
    st.plotly_chart(fig, use_container_width=True)

    st.subheader("Intervention History")
    for record in state["intervention_history"]:
        with st.expander(f"Day {record['day']}: {record['intervention_type']}"):
            st.json(record)


def render_animation_tab(state: EpidemicState, results: dict[str, Any]):
    st.subheader("Epidemic Animation")

    if not results:
        st.info("Run a simulation to see animation")
        return

    metric = create_metric_selector("anim")
    metric_key = [k for k, v in {
        "daily_cases": "Daily Cases",
        "daily_deaths": "Daily Deaths",
        "daily_Rt": "Rt (Reproduction Number)",
        "cumulative_cases": "Cumulative Cases",
        "cumulative_deaths": "Cumulative Deaths",
    }.items() if v == metric][0]

    max_frames = min(
        len(results.get(metric_key, {}).get(state["states"][0], [])),
        100,
    ) if state["states"] else 0

    controls = create_animation_controls("anim", max_frames)

    if results and metric_key in results:
        day_data = {}
        for s in state["states"]:
            values = results[metric_key].get(s, [])
            if controls["frame"] < len(values):
                day_data[s] = values[controls["frame"]]
            else:
                day_data[s] = 0

        fig = create_india_choropleth(
            day_data,
            metric_name=metric,
            title=f"{metric} - Day {controls['frame'] + 1}",
        )
        st.plotly_chart(fig, use_container_width=True, key=f"anim_chart_{controls['frame']}")

        if controls["playing"] and controls["frame"] < max_frames - 1:
            time.sleep(1.0 / controls["speed"])
            st.session_state.animation_frame = controls["frame"] + 1
            st.rerun()


def render_details_tab(state: EpidemicState, results: dict[str, Any], recommendation: dict[str, Any]):
    st.subheader("Simulation Details")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("### Configuration")
        config_data = {
            "Country": state["country"],
            "States": ", ".join(state["states"]),
            "Total Population": format_number(sum(state["population"].values())),
            "Simulation Days": state["simulation_days"],
            "Initial Variant": list(state["active_variants"].values())[0] if state["active_variants"] else "N/A",
            "Interventions": (
                list(set().union(*state["current_policies"].values()))
                if state["current_policies"]
                else "None"
            ),
        }
        for k, v in config_data.items():
            st.text(f"{k}: {v}")

    with col2:
        st.markdown("### Recommendation")
        if recommendation:
            st.json(recommendation)
        else:
            st.info("No recommendation yet")

    st.markdown("### Shock Detection")
    shock = state.get("variant_shock", {})
    if shock.get("shock_detected"):
        st.error(f"⚠️ Variant shock detected! Severity: {shock.get('severity')}")
        st.json(shock)
    else:
        st.success("No variant shock detected")

    st.markdown("### Raw Data Export")
    if st.button("Export Full State as JSON"):
        export_data = {
            "state": {k: v for k, v in state.items() if k != "metadata"},
            "results": results,
            "recommendation": recommendation,
        }
        create_download_button(export_data, "epidemic_state.json", "Download JSON")


def main():
    initialize_session_state()
    render_sidebar()
    render_dashboard()


if __name__ == "__main__":
    main()
