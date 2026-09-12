from __future__ import annotations

import logging
from datetime import datetime

import numpy as np

from ..config import (
    CONFIDENCE_THRESHOLD,
    CONTACT_TRACING_PARAMS,
    MAX_ADAPTATION_LOOPS,
    SHOCK_THRESHOLD,
    SIMULATION_DAYS_PER_STEP,
)
from ..llm import get_llm_client
from ..memory import get_memory_store
from ..state import EpidemicState, VariantShockInfo
from ..tools import (
    calculate_objective,
    detect_variant_shock,
    evaluate_contact_tracing,
    fetch_demographics,
    fetch_epidemic_data,
    simulate_spread,
)

logger = logging.getLogger(__name__)


def _to_python(obj):
    if isinstance(obj, (np.integer,)):
        return int(obj)
    if isinstance(obj, (np.floating,)):
        return float(obj)
    if isinstance(obj, np.ndarray):
        return obj.tolist()
    if isinstance(obj, dict):
        return {k: _to_python(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_to_python(v) for v in obj]
    return obj


def _clean_state(state: EpidemicState) -> EpidemicState:
    for key in state:
        state[key] = _to_python(state[key])
    return state

llm_client = get_llm_client()
memory = get_memory_store()


def analyze_situation(state: EpidemicState) -> EpidemicState:
    logger.info(f"Day {state['current_day']}: Analyzing situation for {state['states']}")

    current_day = state["current_day"]
    states = state["states"]

    data_result = fetch_epidemic_data.invoke({
        "states": states,
        "days_back": 14,
        "metrics": ["cases", "deaths", "tests", "vaccination"],
    })

    demographics = fetch_demographics.invoke({"states": states})

    situation = {
        "day": current_day,
        "states": states,
        "epidemic_data": data_result.get("data", []),
        "demographics": demographics.get("demographics", {}),
        "current_infected": state["infected"],
        "current_Rt": state["Rt_estimates"],
        "active_variants": state["active_variants"],
        "healthcare_capacity": state["healthcare_capacity"],
    }

    similar = memory.query_similar(
        situation_summary=f"Day {current_day}: {sum(state['infected'].values())} cases across {len(states)} states",
        n_results=3,
    )

    state["metadata"]["situation_analysis"] = situation
    state["metadata"]["historical_context"] = similar
    state["metadata"]["last_analysis_day"] = current_day

    return state


def detect_shocks(state: EpidemicState) -> EpidemicState:
    logger.info(f"Day {state['current_day']}: Detecting variant shocks")

    predicted = state["metadata"].get("predicted_outcomes", {})
    actual = state["metadata"].get("situation_analysis", {}).get("epidemic_data", [])

    if not predicted or not actual:
        state["variant_shock"] = VariantShockInfo(
            shock_detected=False,
            anomalies={},
            recommended_action="continue_monitoring",
            severity="none",
        ).model_dump()
        return state

    actual_dict = {}
    for record in actual:
        s = record.get("state")
        if s:
            if s not in actual_dict:
                actual_dict[s] = {"cases": [], "deaths": [], "Rt": []}
            actual_dict[s]["cases"].append(record.get("daily_confirmed", 0))
            actual_dict[s]["deaths"].append(record.get("daily_deceased", 0))

    for s in actual_dict:
        actual_dict[s]["cases"] = actual_dict[s]["cases"][-1] if actual_dict[s]["cases"] else 0
        actual_dict[s]["deaths"] = actual_dict[s]["deaths"][-1] if actual_dict[s]["deaths"] else 0

    shock_result = detect_variant_shock.invoke({
        "predicted": predicted,
        "actual": actual_dict,
        "threshold": SHOCK_THRESHOLD,
    })

    state["variant_shock"] = VariantShockInfo(
        shock_detected=shock_result.get("shock_detected", False),
        anomalies=shock_result.get("anomalies", {}),
        recommended_action=shock_result.get("recommended_action", ""),
        severity=shock_result.get("severity", "none"),
    ).model_dump()

    logger.info(f"Shock detection: {state['variant_shock']}")
    return state


def select_interventions(state: EpidemicState) -> EpidemicState:
    logger.info(f"Day {state['current_day']}: Selecting interventions")

    shock = state.get("variant_shock", {})
    if shock.get("shock_detected"):
        logger.warning(f"Variant shock detected! Severity: {shock.get('severity')}")
        interventions = ["contact_tracing"]
        if shock.get("severity") == "high":
            interventions.append("enhanced_testing")
    else:
        interventions = state["metadata"].get("planned_interventions", ["contact_tracing"])

    intervention_records = []
    for intervention in interventions:
        if intervention == "contact_tracing":
            for s in state["states"]:
                eval_result = evaluate_contact_tracing.invoke({
                    "state": s,
                    "current_cases": state["infected"].get(s, 0),
                    "current_Rt": state["Rt_estimates"].get(s, 1.0),
                    "population": state["population"].get(s),
                    "tracing_efficiency": CONTACT_TRACING_PARAMS["tracing_efficiency"],
                    "isolation_compliance": CONTACT_TRACING_PARAMS["isolation_compliance"],
                    "delay_days": CONTACT_TRACING_PARAMS["delay_days"],
                    "variant": state["active_variants"].get(s, "wildtype"),
                    "projection_days": SIMULATION_DAYS_PER_STEP,
                })

                if eval_result.get("success"):
                    intervention_records.append({
                        "day": state["current_day"],
                        "intervention_type": intervention,
                        "params": CONTACT_TRACING_PARAMS,
                        "cost": eval_result["evaluation"]["cost_inr"],
                        "projected_effect": {
                            "deaths_averted": eval_result["evaluation"]["projected_deaths"],
                            "Rt_reduction": eval_result["evaluation"]["Rt_reduction"],
                        },
                    })

    state["current_policies"] = dict.fromkeys(state["states"], interventions)
    state["intervention_history"].extend(intervention_records)
    state["metadata"]["planned_interventions"] = interventions

    return state


def simulate_outcomes(state: EpidemicState) -> EpidemicState:
    logger.info(f"Day {state['current_day']}: Simulating outcomes")

    all_policies = state["current_policies"].values()
    interventions = list(set().union(*all_policies)) if all_policies else ["contact_tracing"]
    variant = list(state["active_variants"].values())[0] if state["active_variants"] else "wildtype"

    sim_result = simulate_spread.invoke({
        "model_type": "mesa",
        "states": state["states"],
        "variant": variant,
        "days": SIMULATION_DAYS_PER_STEP,
        "interventions": interventions,
        "initial_infected": sum(state["infected"].values()),
        "population": sum(state["population"].values()),
    })

    if sim_result.get("success"):
        result = sim_result["result"]
        state["metadata"]["predicted_outcomes"] = result

        for s in state["states"]:
            state["Rt_estimates"][s] = float(result["daily_Rt"].get(s, [1.0])[-1])

        logger.info(f"Simulation complete. Projected deaths: {sum(result['total_deaths'].values())}")
    else:
        logger.error(f"Simulation failed: {sim_result.get('error')}")
        state["confidence_score"] = max(0.0, state["confidence_score"] - 0.2)

    return state


def evaluate_objective(state: EpidemicState) -> EpidemicState:
    logger.info(f"Day {state['current_day']}: Evaluating objective function")

    predicted = state["metadata"].get("predicted_outcomes", {})
    if not predicted:
        state["objective_value"] = 1.0
        state["confidence_score"] = 0.0
        return state

    total_deaths = sum(predicted.get("total_deaths", {}).values())
    total_pop = sum(state["population"].values())

    economic_cost = sum(r.get("cost", 0) for r in state["intervention_history"] if r.get("day") == state["current_day"])
    social_cost = total_deaths * 100 + economic_cost * 0.01

    max_icu = sum(
        state["healthcare_capacity"].get(s, {}).get("icu_beds", 0)
        for s in state["states"]
    )
    current_icu = sum(
        state["infected"].get(s, 0) * 0.05
        for s in state["states"]
    )
    healthcare_strain = min(current_icu / max(max_icu, 1), 1.0)

    obj_result = calculate_objective.invoke({
        "deaths": total_deaths,
        "population": total_pop,
        "economic_cost": economic_cost,
        "social_cost": social_cost,
        "healthcare_strain": healthcare_strain,
    })

    state["objective_value"] = _to_python(obj_result["total_objective"])
    state["objective_breakdown"] = {
        k: _to_python(v) for k, v in obj_result["breakdown"].items()
    }
    state["confidence_score"] = float(0.8 if state["metadata"].get("predicted_outcomes") else 0.5)

    logger.info(f"Objective value: {state['objective_value']:.4f}")

    return state


def implement_or_adapt(state: EpidemicState) -> EpidemicState:
    logger.info(f"Day {state['current_day']}: Implement or adapt decision")

    shock = state.get("variant_shock", {})
    confidence = state.get("confidence_score", 0.0)

    if shock.get("shock_detected") or confidence < CONFIDENCE_THRESHOLD:
        if state["metadata"].get("adaptation_loops", 0) < MAX_ADAPTATION_LOOPS:
            state["metadata"]["adaptation_loops"] = state["metadata"].get("adaptation_loops", 0) + 1
            state["metadata"]["needs_replan"] = True
            logger.info(f"Adaptation triggered (loop {state['metadata']['adaptation_loops']})")
        else:
            state["metadata"]["needs_replan"] = False
            logger.warning("Max adaptation loops reached, proceeding with current plan")
    else:
        state["metadata"]["needs_replan"] = False

    state["current_day"] += SIMULATION_DAYS_PER_STEP

    return state


def finalize_recommendation(state: EpidemicState) -> EpidemicState:
    logger.info(f"Day {state['current_day']}: Finalizing recommendation")

    interventions = list(set().union(*state["current_policies"].values())) if state["current_policies"] else []
    predicted = state["metadata"].get("predicted_outcomes", {})

    recommendation = {
        "day": state["current_day"] - SIMULATION_DAYS_PER_STEP,
        "states": state["states"],
        "recommended_interventions": interventions,
        "projected_deaths": sum(predicted.get("total_deaths", {}).values()),
        "projected_peak_cases": max(predicted.get("peak_cases", {}).values(), default=0),
        "objective_value": state["objective_value"],
        "objective_breakdown": state["objective_breakdown"],
        "confidence": state["confidence_score"],
        "variant_shock": state["variant_shock"],
        "rationale": _generate_rationale(state),
    }

    state["metadata"]["final_recommendation"] = recommendation
    state["metadata"]["run_complete"] = True

    memory.add_decision(
        decision_id=f"decision_{state['current_day']}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
        day=state["current_day"],
        state=",".join(state["states"]),
        situation_summary=f"Epidemic response decision for {state['states']}",
        intervention=",".join(interventions),
        params={},
        predicted_outcome=predicted,
        objective_value=state["objective_value"],
        confidence=state["confidence_score"],
    )

    return state


def _generate_rationale(state: EpidemicState) -> str:
    parts = []

    shock = state.get("variant_shock", {})
    if shock.get("shock_detected"):
        parts.append(f"Variant shock detected ({shock.get('severity')}): {shock.get('recommended_action')}")

    interventions = list(set().union(*state["current_policies"].values())) if state["current_policies"] else []
    if interventions:
        parts.append(f"Recommended interventions: {', '.join(interventions)}")

    predicted = state["metadata"].get("predicted_outcomes", {})
    if predicted:
        deaths = sum(predicted.get("total_deaths", {}).values())
        parts.append(f"Projected deaths over next {SIMULATION_DAYS_PER_STEP} days: {deaths}")

    parts.append(f"Objective value: {state['objective_value']:.4f} (confidence: {state['confidence_score']:.2f})")

    return " | ".join(parts)
