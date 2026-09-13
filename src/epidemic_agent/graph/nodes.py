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
from ..state import EpidemicState, VariantShockInfo
from ..tools import (
    calculate_objective,
    detect_variant_shock,
    evaluate_contact_tracing,
    evaluate_policy,
    fetch_demographics,
    fetch_epidemic_data,
    simulate_spread,
)
from .reasoning import LLMReasoner
from .learning import ExperienceMemory
from .agents import MultiAgentDebater

logger = logging.getLogger(__name__)


def _get_memory():
    from ..memory import get_memory_store
    return get_memory_store()


_reasoner = LLMReasoner()
_debater = MultiAgentDebater()
_experience_memory = ExperienceMemory()


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


def analyze_situation(state: EpidemicState) -> EpidemicState:
    logger.info(f"Day {state['current_day']}: Analyzing situation for {state['states']}")

    current_day = state["current_day"]
    states = state["states"]
    skip_fetch = state.get("metadata", {}).get("skip_data_fetch", False)

    epidemic_data = []
    demographics = {"demographics": {}}
    learned_params = {}

    if not skip_fetch:
        try:
            data_result = fetch_epidemic_data.invoke({
                "states": states,
                "days_back": 90,
                "metrics": ["cases", "deaths", "tests", "vaccination"],
            })
            epidemic_data = data_result.get("data", [])
        except Exception as e:
            logger.warning(f"Failed to fetch epidemic data: {e}")

        try:
            demographics = fetch_demographics.invoke({"states": states})
        except Exception as e:
            logger.warning(f"Failed to fetch demographics: {e}")

        if epidemic_data:
            try:
                import pandas as pd
                from ..simulation.variant import VariantParameterLearner

                df = pd.DataFrame(epidemic_data)
                learner = VariantParameterLearner()

                for s in states:
                    state_df = df[df["state"] == s].sort_values("date")
                    if len(state_df) < 14:
                        continue

                    cases = state_df["confirmed"].fillna(0)
                    deaths = state_df["deceased"].fillna(0)

                    params = learner.learn_from_wave(
                        cases=cases,
                        deaths=deaths,
                        population=state["population"].get(s, 1_000_000),
                    )
                    matched = learner.match_known_variant(params)
                    learned_params[s] = {
                        "R0": params.R0,
                        "IFR": params.IFR,
                        "immune_escape": params.immune_escape,
                        "serial_interval": params.serial_interval,
                        "matched_variant": matched,
                    }
            except Exception as e:
                logger.warning(f"Variant learning failed: {e}")

    situation = {
        "day": current_day,
        "states": states,
        "epidemic_data": epidemic_data,
        "demographics": demographics.get("demographics", {}),
        "current_infected": state["infected"],
        "current_Rt": state["Rt_estimates"],
        "active_variants": state["active_variants"],
        "healthcare_capacity": state["healthcare_capacity"],
        "learned_params": learned_params,
    }

    try:
        if not skip_fetch:
            similar = _get_memory().query_similar(
                situation_summary=f"Day {current_day}: {sum(state['infected'].values())} cases across {len(states)} states",
                n_results=3,
            )
        else:
            similar = []
    except Exception as e:
        logger.warning(f"Memory query failed: {e}")
        similar = []

    state["metadata"]["situation_analysis"] = situation
    state["metadata"]["historical_context"] = similar
    state["metadata"]["last_analysis_day"] = current_day

    try:
        if not skip_fetch:
            integrate_backtester_accuracy(state)
    except Exception as e:
        logger.warning(f"Backtester accuracy integration skipped: {e}")

    return state


def detect_shocks(state: EpidemicState) -> EpidemicState:
    logger.info(f"Day {state['current_day']}: Detecting variant shocks")

    predicted = state["metadata"].get("predicted_outcomes", {})
    actual = state["metadata"].get("situation_analysis", {}).get("epidemic_data", [])

    if not actual:
        state["variant_shock"] = VariantShockInfo(
            shock_detected=False,
            anomalies={},
            recommended_action="continue_monitoring",
            severity="none",
        ).model_dump()
        return state

    if not predicted:
        state["variant_shock"] = VariantShockInfo(
            shock_detected=False,
            anomalies={},
            recommended_action="first_iteration_no_predictions_yet",
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

    try:
        mapped_predicted = {}
        for state_name in predicted.get("daily_cases", {}):
            cases = predicted.get("daily_cases", {}).get(state_name, [])
            deaths = predicted.get("daily_deaths", {}).get(state_name, [])
            rt = predicted.get("daily_Rt", {}).get(state_name, [])
            mapped_predicted["cases"] = cases[-1] if cases else 0
            mapped_predicted["deaths"] = deaths[-1] if deaths else 0
            mapped_predicted["Rt"] = rt[-1] if rt else 1.0
            break

        shock_result = detect_variant_shock.invoke({
            "predicted": mapped_predicted,
            "actual": actual_dict,
            "threshold": SHOCK_THRESHOLD,
        })
    except Exception as e:
        logger.warning(f"Shock detection failed: {e}")
        shock_result = {"shock_detected": False, "anomalies": {}, "recommended_action": "", "severity": "none"}

    state["variant_shock"] = VariantShockInfo(
        shock_detected=shock_result.get("shock_detected", False),
        anomalies=shock_result.get("anomalies", {}),
        recommended_action=shock_result.get("recommended_action", ""),
        severity=shock_result.get("severity", "none"),
    ).model_dump()

    logger.info(f"Shock detection: {state['variant_shock']}")
    return state


def llm_reasoning(state: EpidemicState) -> EpidemicState:
    logger.info(f"Day {state['current_day']}: LLM Reasoning")

    reasoning_input = {
        "current_day": state["current_day"],
        "infected": state["infected"],
        "deceased": state["deceased"],
        "population": state["population"],
        "Rt_estimates": state["Rt_estimates"],
        "active_variants": state["active_variants"],
        "healthcare_capacity": state["healthcare_capacity"],
        "cumulative_cases": state.get("cumulative_cases", {}),
    }

    history = state.get("metadata", {}).get("reasoning_history", [])
    try:
        result = _reasoner.reason(reasoning_input, history)
    except Exception as e:
        logger.warning(f"Reasoning failed: {e}")
        from .reasoning import ReasoningResult
        result = ReasoningResult(
            severity="medium",
            rationale=f"Reasoning failed: {e}",
            recommended_policies=["contact_tracing", "social_distancing", "mask_mandate", "enhanced_testing"],
            confidence=0.3,
            uncertainty_factors=["reasoning_module_error"],
            policy_ranking=[],
            failure_detected=False,
            failure_type="reasoning_error",
            recovery_action=f"Using fallback policies due to: {e}",
        )

    state["metadata"]["reasoning_result"] = {
        "severity": result.severity,
        "rationale": result.rationale,
        "recommended_policies": result.recommended_policies,
        "confidence": result.confidence,
        "uncertainty_factors": result.uncertainty_factors,
        "failure_detected": result.failure_detected,
        "failure_type": result.failure_type,
        "recovery_action": result.recovery_action,
    }

    if result.failure_detected:
        logger.warning(f"FAILURE DETECTED: {result.failure_type}. Recovery: {result.recovery_action}")
        state["metadata"]["needs_recovery"] = True
        state["metadata"]["recovery_action"] = result.recovery_action
        state["confidence_score"] = max(0.1, state["confidence_score"] - 0.3)
    else:
        state["metadata"]["needs_recovery"] = False

    history.append({
        "day": state["current_day"],
        "severity": result.severity,
        "confidence": result.confidence,
    })
    state["metadata"]["reasoning_history"] = history[-20:]

    logger.info(f"Reasoning: severity={result.severity}, confidence={result.confidence:.2f}")
    return state


def multi_agent_debate(state: EpidemicState) -> EpidemicState:
    logger.info(f"Day {state['current_day']}: Multi-Agent Debate")

    reasoning = state.get("metadata", {}).get("reasoning_result", {})
    severity = reasoning.get("severity", "medium")

    if reasoning.get("failure_detected"):
        logger.info("Skipping debate due to failure detection")
        state["metadata"]["debate_result"] = {
            "consensus_policies": ["enhanced_testing", "contact_tracing"],
            "agreement_score": 0.5,
            "reasoning": "Failure detected - using emergency protocols",
        }
        return state

    candidate_policies = reasoning.get("recommended_policies", [
        "contact_tracing", "social_distancing", "mask_mandate", "enhanced_testing",
    ])

    debate_input = {
        "current_day": state["current_day"],
        "infected": state["infected"],
        "deceased": state["deceased"],
        "population": state["population"],
        "Rt_estimates": state["Rt_estimates"],
        "active_variants": state["active_variants"],
        "healthcare_capacity": state["healthcare_capacity"],
    }

    try:
        debate_result = _debater.debate(candidate_policies, debate_input, severity, rounds=2)
    except Exception as e:
        logger.warning(f"Debate failed: {e}")
        from .agents import DebateResult
        debate_result = DebateResult(
            consensus_policies=candidate_policies[:2] if candidate_policies else [],
            agreement_score=0.5,
            dissenting_opinions=[],
            reasoning=f"Debate failed: {e}",
        )

    state["metadata"]["debate_result"] = {
        "consensus_policies": debate_result.consensus_policies,
        "agreement_score": debate_result.agreement_score,
        "dissenting_opinions": debate_result.dissenting_opinions,
        "reasoning": debate_result.reasoning,
    }

    if debate_result.agreement_score < 0.3:
        state["confidence_score"] = max(0.2, state["confidence_score"] - 0.1)
        logger.warning(f"Low agreement in debate: {debate_result.agreement_score:.2f}")

    logger.info(f"Debate consensus: {debate_result.consensus_policies}, agreement={debate_result.agreement_score:.2f}")
    return state


def select_interventions(state: EpidemicState) -> EpidemicState:
    logger.info(f"Day {state['current_day']}: Selecting interventions")

    shock = state.get("variant_shock", {})
    reasoning = state.get("metadata", {}).get("reasoning_result", {})
    debate = state.get("metadata", {}).get("debate_result", {})

    if state["metadata"].get("needs_recovery"):
        interventions = ["enhanced_testing", "contact_tracing", "quarantine"]
        logger.info(f"Using emergency recovery policies")
    elif shock.get("shock_detected"):
        logger.warning(f"Variant shock detected! Severity: {shock.get('severity')}")
        if shock.get("severity") == "high":
            interventions = [
                "lockdown", "mask_mandate", "travel_restrictions",
                "quarantine", "enhanced_testing", "contact_tracing",
                "social_distancing",
            ]
        elif shock.get("severity") == "medium":
            interventions = [
                "mask_mandate", "travel_restrictions", "quarantine",
                "enhanced_testing", "contact_tracing", "social_distancing",
            ]
        else:
            interventions = [
                "contact_tracing", "enhanced_testing", "mask_mandate",
                "social_distancing",
            ]
    elif debate.get("consensus_policies"):
        interventions = debate["consensus_policies"]
        logger.info(f"Using debate consensus: {interventions}")
    else:
        severity = reasoning.get("severity", "medium")
        advice = _experience_memory.get_policy_advice(severity)
        if advice["best_policies"] and advice["confidence"] > 0.3:
            interventions = advice["best_policies"]
            logger.info(f"Using learned policies: {interventions}")
        else:
            interventions = state["metadata"].get("planned_interventions", [
                "contact_tracing", "social_distancing", "mask_mandate",
                "enhanced_testing",
            ])

    state_scores: dict[str, list[tuple[str, float]]] = {s: [] for s in state["states"]}
    intervention_records = []
    for intervention in interventions:
        for s in state["states"]:
            try:
                eval_result = evaluate_policy.invoke({
                    "policy": intervention,
                    "state": s,
                    "current_state": {
                        "infected": state["infected"],
                        "Rt_estimates": state["Rt_estimates"],
                        "population": state["population"],
                    },
                    "variant": state["active_variants"].get(s, "wildtype"),
                    "projection_days": SIMULATION_DAYS_PER_STEP,
                })
            except Exception as e:
                logger.warning(f"Policy evaluation failed for {intervention}/{s}: {e}")
                eval_result = {"success": False}

            if eval_result.get("success"):
                score = eval_result["evaluation"].get("Rt_reduction", 0) - (eval_result["evaluation"].get("cost_inr", 0) / max(state["population"].get(s, 1), 1))
                state_scores[s].append((intervention, score))
                intervention_records.append({
                    "day": state["current_day"],
                    "intervention_type": intervention,
                    "state": s,
                    "cost": eval_result["evaluation"]["cost_inr"],
                    "projected_effect": {
                        "deaths_averted": eval_result["evaluation"]["projected_deaths"],
                        "Rt_reduction": eval_result["evaluation"]["Rt_reduction"],
                    },
                })

    state_policies = {}
    for s in state["states"]:
        scored = state_scores[s]
        if scored:
            scored.sort(key=lambda x: x[1], reverse=True)
            state_policies[s] = [p for p, _ in scored[:4]]
        else:
            state_policies[s] = list(interventions)

    state["current_policies"] = state_policies
    state["intervention_history"].extend(intervention_records)
    state["metadata"]["planned_interventions"] = interventions

    return state


def simulate_outcomes(state: EpidemicState) -> EpidemicState:
    logger.info(f"Day {state['current_day']}: Simulating outcomes")

    if state["metadata"].get("awaiting_human_approval"):
        logger.info("Human approval pending — skipping simulation")
        return state

    all_policies = list(state["current_policies"].values())
    if all_policies:
        interventions = list(set().union(*all_policies))
    else:
        interventions = ["contact_tracing"]

    if state["active_variants"]:
        variant = max(state["active_variants"].values(), key=lambda v: list(state["active_variants"].values()).count(v))
    else:
        variant = "wildtype"

    total_population = min(sum(state["population"].values()), 1_000_000)

    sim_result = simulate_spread.invoke({
        "model_type": "seir",
        "states": state["states"],
        "variant": variant,
        "days": SIMULATION_DAYS_PER_STEP,
        "interventions": interventions,
        "initial_infected": min(sum(state["infected"].values()), total_population // 100),
        "population": total_population,
    })

    if sim_result.get("success"):
        result = sim_result["result"]
        state["metadata"]["predicted_outcomes"] = result

        for s in state["states"]:
            rt_list = result.get("daily_Rt", {}).get(s, [])
            if rt_list:
                state["Rt_estimates"][s] = float(rt_list[-1])

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
        state["objective_breakdown"] = {"deaths": 0, "economic": 0, "social": 0, "healthcare": 0}
        return state

    total_deaths = sum(predicted.get("total_deaths", {}).values())
    total_pop = sum(state["population"].values())

    economic_cost = sum(r.get("cost", 0) for r in state["intervention_history"] if r.get("day") == state["current_day"])
    social_cost = total_deaths * 100 + economic_cost * 0.01

    max_icu = sum(
        state["healthcare_capacity"].get(s, {}).get("icu", 0)
        for s in state["states"]
    )
    current_icu = sum(
        state["infected"].get(s, 0) * 0.05
        for s in state["states"]
    )
    healthcare_strain = min(current_icu / max(max_icu, 1), 1.0)

    try:
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
    except Exception as e:
        logger.warning(f"Objective calculation failed: {e}")
        state["objective_value"] = 0.5
        state["objective_breakdown"] = {"deaths": 0, "economic": 0, "social": 0, "healthcare": 0}

    obj = state["objective_value"]
    if obj < 0.3:
        state["confidence_score"] = min(state["confidence_score"] + 0.05, 1.0)
    elif obj > 0.7:
        state["confidence_score"] = max(state["confidence_score"] - 0.05, 0.0)

    logger.info(f"Objective value: {state['objective_value']:.4f}")

    return state


def implement_or_adapt(state: EpidemicState) -> EpidemicState:
    logger.info(f"Day {state['current_day']}: Implement or adapt decision")

    shock = state.get("variant_shock", {})
    confidence = state.get("confidence_score", 0.0)
    total_sim_days = state.get("simulation_days", 21)

    if state["current_day"] + SIMULATION_DAYS_PER_STEP >= total_sim_days:
        state["metadata"]["needs_replan"] = False
        state["current_day"] += SIMULATION_DAYS_PER_STEP
        return state

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

    all_policies = list(state["current_policies"].values())
    interventions = list(set().union(*all_policies)) if all_policies else []
    predicted = state["metadata"].get("predicted_outcomes", {})
    reasoning = state.get("metadata", {}).get("reasoning_result", {})

    recommendation = {
        "day": state["current_day"],
        "states": state["states"],
        "recommended_interventions": interventions,
        "projected_deaths": sum(predicted.get("total_deaths", {}).values()),
        "projected_peak_cases": max(predicted.get("peak_cases", {}).values(), default=0),
        "objective_value": state["objective_value"],
        "objective_breakdown": state["objective_breakdown"],
        "confidence": state["confidence_score"],
        "variant_shock": state["variant_shock"],
        "rationale": _generate_rationale(state),
        "severity": reasoning.get("severity", "unknown"),
        "debate_agreement": state.get("metadata", {}).get("debate_result", {}).get("agreement_score", 0),
        "failure_detected": reasoning.get("failure_detected", False),
    }

    state["metadata"]["final_recommendation"] = recommendation
    state["metadata"]["run_complete"] = True

    outcome = {
        "deaths": sum(predicted.get("total_deaths", {}).values()),
        "r0_after": list(state["Rt_estimates"].values())[0] if state["Rt_estimates"] else 1.0,
        "r0_reduction": 0.0,
        "deaths_averted": 0.0,
        "economic_cost": sum(r.get("cost", 0) for r in state["intervention_history"]),
    }

    _experience_memory.record_experience(
        day=state["current_day"],
        state=state,
        policies=interventions,
        severity=reasoning.get("severity", "medium"),
        outcome=outcome,
        rationale=reasoning.get("rationale", ""),
        confidence=state["confidence_score"],
    )

    try:
        _get_memory().add_decision(
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
    except Exception as e:
        logger.warning(f"Failed to save decision to memory: {e}")

    return state


def _generate_rationale(state: EpidemicState) -> str:
    parts = []

    shock = state.get("variant_shock", {})
    if shock.get("shock_detected"):
        parts.append(f"Variant shock detected ({shock.get('severity')}): {shock.get('recommended_action')}")

    all_policies = list(state["current_policies"].values())
    interventions = list(set().union(*all_policies)) if all_policies else []
    if interventions:
        parts.append(f"Recommended interventions: {', '.join(interventions)}")

    predicted = state["metadata"].get("predicted_outcomes", {})
    if predicted:
        deaths = sum(predicted.get("total_deaths", {}).values())
        parts.append(f"Projected deaths over next {SIMULATION_DAYS_PER_STEP} days: {deaths}")

    parts.append(f"Objective value: {state['objective_value']:.4f} (confidence: {state['confidence_score']:.2f})")

    return " | ".join(parts)


def human_approval_gate(state: EpidemicState) -> EpidemicState:
    """Pauses workflow for human approval of proposed interventions.
    Sets metadata flags that the API layer checks to pause/resume.
    """
    logger.info(f"Day {state['current_day']}: Human approval gate")

    all_policies = list(state["current_policies"].values())
    interventions = list(set().union(*all_policies)) if all_policies else []

    state["metadata"]["awaiting_human_approval"] = True
    state["metadata"]["proposed_interventions"] = interventions
    state["metadata"]["approval_timestamp"] = None
    state["metadata"]["human_modifications"] = {}

    logger.info(f"Awaiting human approval for: {interventions}")
    return state


def approve_human_interventions(state: EpidemicState, approved_interventions: list[str] = None,
                                 human_notes: str = "") -> EpidemicState:
    """Called by the API when human approves/modifies interventions.
    Updates state with approved interventions and clears the approval flag.
    """
    if approved_interventions is not None:
        for s in state["states"]:
            state["current_policies"][s] = approved_interventions

    state["metadata"]["awaiting_human_approval"] = False
    state["metadata"]["human_approved"] = True
    state["metadata"]["human_notes"] = human_notes
    state["metadata"]["approval_timestamp"] = datetime.now().isoformat()

    logger.info(f"Human approved interventions: {approved_interventions}")
    return state


def integrate_backtester_accuracy(state: EpidemicState) -> EpidemicState:
    """Adjusts confidence score based on historical backtest accuracy.
    Called during analyze_situation to calibrate confidence against known model performance.
    """
    try:
        from ..validation.backtester import Backtester
        from ..config import VARIANT_PARAMS

        backtester = Backtester()
        variant = state["active_variants"].get(state["states"][0], "wildtype") if state["active_variants"] else "wildtype"

        variant_params = VARIANT_PARAMS.get(variant, VARIANT_PARAMS["wildtype"])

        total_r2 = 0.0
        total_corr = 0.0
        n_states = 0

        for s in state["states"][:3]:
            try:
                result = backtester.backtest_state(
                    state=s, variant=variant,
                    start_date="2021-04-01", end_date="2021-06-30",
                    run_cv=False,
                )
                if result.metrics.r_squared != 0 or result.metrics.correlation != 0:
                    total_r2 += result.metrics.r_squared
                    total_corr += result.metrics.correlation
                    n_states += 1
            except Exception:
                pass

        if n_states > 0:
            avg_r2 = total_r2 / n_states
            avg_corr = total_corr / n_states

            accuracy_factor = max(0.5, min(1.0, (avg_r2 + avg_corr) / 2 + 0.5))
            state["confidence_score"] = min(state["confidence_score"], accuracy_factor)

            state["metadata"]["backtester_accuracy"] = {
                "avg_r2": round(avg_r2, 4),
                "avg_correlation": round(avg_corr, 4),
                "accuracy_factor": round(accuracy_factor, 4),
                "states_evaluated": n_states,
            }
            logger.info(f"Backtester accuracy: R2={avg_r2:.3f}, Corr={avg_corr:.3f}, factor={accuracy_factor:.3f}")
        else:
            state["metadata"]["backtester_accuracy"] = {"avg_r2": 0, "avg_correlation": 0, "accuracy_factor": 0.75, "states_evaluated": 0}

    except Exception as e:
        logger.warning(f"Backtester integration failed: {e}")
        state["metadata"]["backtester_accuracy"] = {"error": str(e)}

    return state
