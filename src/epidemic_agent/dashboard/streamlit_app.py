from __future__ import annotations

from typing import Any

import streamlit as st

from epidemic_agent.config import INDIA_STATES, VARIANT_PARAMS, get_state_population
from epidemic_agent.dashboard.components import (
    METRIC_LABELS,
    create_animated_choropleth,
    create_animation_controls,
    create_deaths_cases_dual_axis,
    create_india_choropleth,
    create_intervention_timeline,
    create_metric_selector,
    create_multi_metric_figure,
    create_rt_heatmap,
    create_state_selector,
)
from epidemic_agent.dashboard.utils import create_download_button, display_objective_breakdown, format_number
from epidemic_agent.graph import get_workflow
from epidemic_agent.persistence import get_state_store
from epidemic_agent.state import EpidemicState, SimulationConfig
from epidemic_agent.tools import fetch_epidemic_data

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


def create_initial_state(config: SimulationConfig) -> EpidemicState:
    population = {}
    for state in config.states:
        population[state] = get_state_population(state)

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

    - **Monitors** real-time epidemic data from data.incovid19.org and CoWIN
    - **Simulates** disease spread using agent-based (Mesa) and compartmental (SEIR) models
    - **Adapts** to variant shocks through dynamic detection and re-planning
    - **Optimizes** interventions using a multi-objective function (deaths, economy, society, healthcare)
    - **Learns** variant parameters from observed epidemic waves

    **Get started:** Select "New Simulation" in the sidebar to configure and run a simulation.

    You can also explore the **Backtesting**, **Sensitivity**, and **Uncertainty** tabs below without running a simulation.
    """)

    render_validation_tabs()


def render_validation_tabs():
    tab_bt, tab_sa, tab_uq = st.tabs(["🔬 Backtesting", "📊 Sensitivity", "🎯 Uncertainty"])

    with tab_bt:
        render_backtesting_tab()

    with tab_sa:
        render_sensitivity_tab()

    with tab_uq:
        render_uncertainty_tab()


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
    tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8 = st.tabs([
        "🗺️ Map View",
        "📈 Metrics",
        "⏱️ Timeline",
        "🎬 Animation",
        "📋 Details",
        "🔬 Backtesting",
        "📊 Sensitivity",
        "🎯 Uncertainty",
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

    with tab6:
        render_backtesting_tab()

    with tab7:
        render_sensitivity_tab()

    with tab8:
        render_uncertainty_tab()


def render_map_tab(state: EpidemicState, results: dict[str, Any]):
    st.subheader("Epidemic Map")

    col1, col2 = st.columns([3, 1])

    with col2:
        metric = create_metric_selector("map")
        metric_key = [k for k, v in METRIC_LABELS.items() if v == metric][0]
        selected_state = create_state_selector(state["states"], "map")

    with col1:
        if results and metric_key in results:
            if selected_state == "All":
                display_states = state["states"]
            else:
                display_states = [selected_state]

            day_data = {}
            for s in display_states:
                values = results[metric_key].get(s, [])
                day_data[s] = values[-1] if values else 0

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
        default=["daily_cases", "daily_deaths"],
        key="metrics_list",
    )

    days = st.slider("Days to show", 7, state["simulation_days"], min(60, state["simulation_days"]))

    fig = create_multi_metric_figure(results, selected_states, metrics, days)
    st.plotly_chart(fig, use_container_width=True)

    st.subheader("Reproduction Number (Rt) by State")
    fig_rt = create_rt_heatmap(results, selected_states, days)
    st.plotly_chart(fig_rt, use_container_width=True)

    st.subheader("Cases vs Deaths")
    fig_dc = create_deaths_cases_dual_axis(results, selected_states, days)
    st.plotly_chart(fig_dc, use_container_width=True)

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
    metric_key = [k for k, v in METRIC_LABELS.items() if v == metric][0]

    n_days = min(
        max(len(v) for v in results.get(metric_key, {}).values()) if results.get(metric_key) else 0,
        100,
    )

    controls = create_animation_controls("anim", n_days)

    if results and metric_key in results and n_days > 0:
        fig = create_animated_choropleth(results, state["states"], metric_key, metric)

        if controls["frame"] < n_days:
            fig.update_layout(title=f"Day {controls['frame'] + 1} — {metric}")

        st.plotly_chart(fig, use_container_width=True)


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
        st.error(f"Variant shock detected! Severity: {shock.get('severity')}")
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


def render_backtesting_tab():
    st.subheader("Backtesting Against Real India COVID-19 Data")

    import numpy as np
    import pandas as pd
    import plotly.graph_objects as go
    from epidemic_agent.validation.backtester import Backtester

    st.markdown("""
    Compare model predictions against real COVID-19 data from **data.incovid19.org**.
    Tests on Delta, Omicron, and First Wave periods for Maharashtra.
    """)

    state_options = ["Maharashtra", "Delhi", "Karnataka", "Kerala", "Tamil Nadu"]
    selected_state = st.selectbox("Select State", state_options, key="bt_state")

    variant_options = {
        "Delta Wave (Apr-Jun 2021)": ("2021-04-01", "2021-06-30", "delta"),
        "Omicron Wave (Jan-Mar 2022)": ("2022-01-01", "2022-03-31", "omicron_ba1"),
        "First Wave (Sep-Dec 2020)": ("2020-09-01", "2020-12-31", "wildtype"),
    }
    selected_wave = st.selectbox("Select Wave", list(variant_options.keys()), key="bt_wave")

    if st.button("Run Backtest", type="primary", key="bt_run"):
        start_date, end_date, variant = variant_options[selected_wave]
        bt = Backtester()

        with st.spinner(f"Fetching real data for {selected_state}..."):
            df = bt.fetch_state_timeseries(selected_state, start_date, end_date)

        if df is None or len(df) == 0:
            st.error("Could not fetch real data. Check your internet connection.")
            return

        from epidemic_agent.config import get_state_population
        population = get_state_population(selected_state)
        days = len(df)
        initial_infected = max(int(df["daily_confirmed"].iloc[0]) if "daily_confirmed" in df.columns else 100, 10)

        from epidemic_agent.simulation.seir_model import SEIRModel
        from epidemic_agent.simulation.variant import VariantParameterLearner

        real_dc = df["daily_confirmed"].fillna(0).values[:days]
        real_dd = df["daily_deceased"].fillna(0).values[:days]

        with st.spinner("Learning variant parameters from real data..."):
            learner = VariantParameterLearner()
            learned = learner.learn_from_wave(
                df["confirmed"], df["deceased"],
                population=population, vax_rate=0.3,
            )

        from epidemic_agent.config import VARIANT_PARAMS
        known_params = VARIANT_PARAMS.get(variant, VARIANT_PARAMS["wildtype"])

        known_model = SEIRModel(
            population=population, R0=known_params["R0"], IFR=known_params["IFR"],
            immune_escape=known_params["immune_escape"],
            serial_interval=known_params["serial_interval"],
            incubation_period=5.2, infectious_period=7.0,
            days=days, states=[selected_state], initial_infected=initial_infected,
        )
        known_result = known_model.run()

        learned_model = SEIRModel(
            population=population, R0=learned.R0, IFR=learned.IFR,
            immune_escape=learned.immune_escape,
            serial_interval=learned.serial_interval,
            incubation_period=5.2, infectious_period=7.0,
            days=days, states=[selected_state], initial_infected=initial_infected,
        )
        learned_result = learned_model.run()

        sim_cases_known = np.array(known_result.daily_cases.get(selected_state, [0] * days))[:days]
        sim_deaths_known = np.array(known_result.daily_deaths.get(selected_state, [0] * days))[:days]
        sim_cases_learned = np.array(learned_result.daily_cases.get(selected_state, [0] * days))[:days]
        sim_deaths_learned = np.array(learned_result.daily_deaths.get(selected_state, [0] * days))[:days]

        r_max = max(np.max(real_dc), 1)
        s_max_known = max(np.max(sim_cases_known), 1)
        s_max_learned = max(np.max(sim_cases_learned), 1)

        corr_known_cases = float(np.corrcoef(real_dc / r_max, sim_cases_known / s_max_known)[0, 1]) if days > 1 else 0
        corr_learned_cases = float(np.corrcoef(real_dc / r_max, sim_cases_learned / s_max_learned)[0, 1]) if days > 1 else 0

        rd_max = max(np.max(real_dd), 1)
        sd_max_known = max(np.max(sim_deaths_known), 1)
        sd_max_learned = max(np.max(sim_deaths_learned), 1)

        corr_known_deaths = float(np.corrcoef(real_dd / rd_max, sim_deaths_known / sd_max_known)[0, 1]) if days > 1 else 0
        corr_learned_deaths = float(np.corrcoef(real_dd / rd_max, sim_deaths_learned / sd_max_learned)[0, 1]) if days > 1 else 0

        st.markdown(f"### {selected_wave} — {selected_state}")

        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Learned R0", f"{learned.R0:.2f}", f"{known_params['R0']:.1f} actual")
        with col2:
            st.metric("Learned IFR", f"{learned.IFR:.4f}", f"{known_params['IFR']:.3f} actual")
        with col3:
            st.metric("Correlation (Cases)", f"{max(corr_known_cases, corr_learned_cases):.3f}")

        st.markdown("#### Daily Cases: Real vs Simulated")
        fig_cases = go.Figure()
        fig_cases.add_trace(go.Scatter(y=real_dc, name="Real Cases", line=dict(color="white")))
        fig_cases.add_trace(go.Scatter(y=sim_cases_known, name=f"SEIR (R0={known_params['R0']})", line=dict(color="blue", dash="dash")))
        fig_cases.add_trace(go.Scatter(y=sim_cases_learned, name=f"SEIR (Learned R0={learned.R0:.1f})", line=dict(color="orange")))
        fig_cases.update_layout(xaxis_title="Day", yaxis_title="Daily Cases", template="plotly_dark")
        st.plotly_chart(fig_cases, use_container_width=True)

        st.markdown("#### Daily Deaths: Real vs Simulated")
        fig_deaths = go.Figure()
        fig_deaths.add_trace(go.Scatter(y=real_dd, name="Real Deaths", line=dict(color="white")))
        fig_deaths.add_trace(go.Scatter(y=sim_deaths_known, name=f"SEIR (IFR={known_params['IFR']})", line=dict(color="red", dash="dash")))
        fig_deaths.add_trace(go.Scatter(y=sim_deaths_learned, name=f"SEIR (Learned IFR={learned.IFR:.4f})", line=dict(color="orange")))
        fig_deaths.update_layout(xaxis_title="Day", yaxis_title="Daily Deaths", template="plotly_dark")
        st.plotly_chart(fig_deaths, use_container_width=True)

        st.info("**Note:** Absolute counts are overpredicted because the SEIR model does not model behavioral changes or interventions. Curve shape (timing, peak) is the meaningful comparison.")


def render_sensitivity_tab():
    st.subheader("Sensitivity Analysis")

    import numpy as np
    import plotly.graph_objects as go
    from epidemic_agent.validation.sensitivity import SensitivityAnalyzer

    st.markdown("Analyze which parameters most affect epidemic outcomes.")

    variant = st.selectbox(
        "Variant",
        ["wildtype", "delta", "omicron_ba1"],
        key="sa_variant",
    )
    days = st.slider("Simulation days", 30, 120, 60, key="sa_days")

    if st.button("Run Analysis", type="primary", key="sa_run"):
        with st.spinner("Running sensitivity analysis..."):
            analyzer = SensitivityAnalyzer(variant=variant, days=days)
            sa = analyzer.run_full_analysis()

        st.markdown("### Parameter Importance")
        importance = sa.parameter_importance
        fig_imp = go.Figure(go.Bar(
            x=list(importance.values()),
            y=list(importance.keys()),
            orientation="h",
            marker_color="#FF4B4B",
        ))
        fig_imp.update_layout(
            xaxis_title="Relative Importance",
            template="plotly_dark",
            height=300,
        )
        st.plotly_chart(fig_imp, use_container_width=True)

        st.markdown("### Parameter Sensitivities")
        for r in sa.results:
            with st.expander(f"{r.parameter} (base={r.base_value}, elasticity={r.elasticity:.3f})"):
                fig_param = go.Figure(go.Scatter(
                    x=r.variation_range,
                    y=r.sensitivities,
                    mode="lines+markers",
                    line=dict(color="#FF4B4B"),
                ))
                fig_param.update_layout(
                    xaxis_title=r.parameter,
                    yaxis_title="Sensitivity",
                    template="plotly_dark",
                )
                st.plotly_chart(fig_param, use_container_width=True)

        st.json(sa.summary())


def render_uncertainty_tab():
    st.subheader("Uncertainty Quantification")

    import numpy as np
    import plotly.graph_objects as go
    from epidemic_agent.validation.uncertainty import UncertaintyQuantifier

    st.markdown("Monte Carlo simulation with parameter perturbation to quantify prediction uncertainty.")

    variant = st.selectbox(
        "Variant",
        ["wildtype", "delta", "omicron_ba1"],
        key="uq_variant",
    )
    days = st.slider("Simulation days", 30, 120, 90, key="uq_days")
    n_sims = st.slider("Number of simulations", 20, 200, 50, key="uq_n_sims")

    if st.button("Run Uncertainty Analysis", type="primary", key="uq_run"):
        with st.spinner(f"Running {n_sims} Monte Carlo simulations..."):
            uq = UncertaintyQuantifier(variant=variant, days=days, n_simulations=n_sims)
            result = uq.quantify()

        s = result.summary()
        st.markdown("### Summary")
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Mean Deaths", f"{s['mean_deaths']:,.0f}", f"+/- {s['std_deaths']:,.0f}")
        with col2:
            st.metric("95% CI Deaths", s["95%_CI_deaths"])
        with col3:
            st.metric("Confidence Score", f"{s['confidence_score']:.3f}")

        st.markdown("### Cases: Mean with 95% CI Band")
        cases_band = result.daily_cases_band
        x = list(range(len(cases_band.median)))
        fig_cases = go.Figure()
        fig_cases.add_trace(go.Scatter(
            x=x + x[::-1],
            y=cases_band.upper + cases_band.lower[::-1],
            fill="toself",
            fillcolor="rgba(255,75,75,0.2)",
            line=dict(color="rgba(255,75,75,0)"),
            name="95% CI",
        ))
        fig_cases.add_trace(go.Scatter(
            x=x,
            y=cases_band.median,
            name="Median",
            line=dict(color="#FF4B4B"),
        ))
        fig_cases.update_layout(xaxis_title="Day", yaxis_title="Daily Cases", template="plotly_dark")
        st.plotly_chart(fig_cases, use_container_width=True)

        st.markdown("### Deaths: Mean with 95% CI Band")
        deaths_band = result.daily_deaths_band
        x = list(range(len(deaths_band.median)))
        fig_deaths = go.Figure()
        fig_deaths.add_trace(go.Scatter(
            x=x + x[::-1],
            y=deaths_band.upper + deaths_band.lower[::-1],
            fill="toself",
            fillcolor="rgba(255,75,75,0.2)",
            line=dict(color="rgba(255,75,75,0)"),
            name="95% CI",
        ))
        fig_deaths.add_trace(go.Scatter(
            x=x,
            y=deaths_band.median,
            name="Median",
            line=dict(color="#FF4B4B"),
        ))
        fig_deaths.update_layout(xaxis_title="Day", yaxis_title="Daily Deaths", template="plotly_dark")
        st.plotly_chart(fig_deaths, use_container_width=True)

        st.json(s)


def main():
    initialize_session_state()
    render_sidebar()
    render_dashboard()


if __name__ == "__main__":
    main()
