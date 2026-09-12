from __future__ import annotations

import logging
from dataclasses import asdict, dataclass
from typing import Any

from ..config import (
    CONTACT_TRACING_PARAMS,
    INCUBATION_PERIOD,
    INFECTIOUS_PERIOD,
    get_state_population,
    get_variant_params,
)
from ..simulation.seir_model import run_seir_simulation
from .registry import register_tool

logger = logging.getLogger(__name__)


@dataclass
class PolicyEvaluation:
    policy: str
    state: str
    projected_cases: int
    projected_deaths: int
    projected_peak_day: int
    projected_peak_cases: int
    Rt_reduction: float
    cost_inr: float
    cost_per_death_averted: float
    confidence: float


@register_tool(description="Evaluate contact tracing intervention effectiveness for a state")
def evaluate_contact_tracing(
    state: str,
    current_cases: int,
    current_Rt: float,
    population: int = None,
    tracing_efficiency: float = None,
    isolation_compliance: float = None,
    delay_days: int = None,
    variant: str = "wildtype",
    projection_days: int = 30,
) -> dict[str, Any]:
    population = population or get_state_population(state)
    tracing_efficiency = tracing_efficiency or CONTACT_TRACING_PARAMS["tracing_efficiency"]
    isolation_compliance = isolation_compliance or CONTACT_TRACING_PARAMS["isolation_compliance"]
    delay_days = delay_days or CONTACT_TRACING_PARAMS["delay_days"]

    variant_params = get_variant_params(variant)

    base_params = {
        "R0": variant_params["R0"],
        "IFR": variant_params["IFR"],
        "immune_escape": variant_params["immune_escape"],
        "serial_interval": variant_params["serial_interval"],
        "incubation_period": INCUBATION_PERIOD,
        "infectious_period": INFECTIOUS_PERIOD,
        "population": population,
        "initial_infected": current_cases,
        "days": projection_days,
        "states": [state],
        "contact_tracing_enabled": False,
    }

    intervention_params = base_params.copy()
    intervention_params.update({
        "contact_tracing_enabled": True,
        "tracing_efficiency": tracing_efficiency,
        "isolation_compliance": isolation_compliance,
        "tracing_delay": delay_days,
    })

    try:
        base_result = run_seir_simulation(**base_params)
        int_result = run_seir_simulation(**intervention_params)
    except Exception as e:
        logger.error(f"SEIR simulation failed: {e}")
        return {"success": False, "error": str(e)}

    base_deaths = base_result.total_deaths.get(state, 0)
    int_deaths = int_result.total_deaths.get(state, 0)
    deaths_averted = max(base_deaths - int_deaths, 0)

    base_peak = base_result.peak_cases.get(state, 0)
    int_peak = int_result.peak_cases.get(state, 0)

    base_Rt = base_result.daily_Rt.get(state, [1.0])[-1]
    int_Rt = int_result.daily_Rt.get(state, [1.0])[-1]
    Rt_reduction = max(base_Rt - int_Rt, 0)

    traces_needed = int(current_cases * tracing_efficiency * 10)
    cost = traces_needed * CONTACT_TRACING_PARAMS["cost_per_trace_inr"]
    cost_per_death = cost / max(deaths_averted, 1)

    eval_result = PolicyEvaluation(
        policy="contact_tracing",
        state=state,
        projected_cases=int_result.cumulative_cases.get(state, [0])[-1],
        projected_deaths=int_deaths,
        projected_peak_day=int_result.peak_day.get(state, 0),
        projected_peak_cases=int_peak,
        Rt_reduction=Rt_reduction,
        cost_inr=cost,
        cost_per_death_averted=cost_per_death,
        confidence=0.75,
    )

    return {"success": True, "evaluation": asdict(eval_result)}


@register_tool(description="Evaluate intervention policy effectiveness (contact tracing, lockdown, vaccination, etc.)")
def evaluate_policy(
    policy: str,
    state: str,
    current_state: dict[str, Any],
    variant: str = "wildtype",
    projection_days: int = 30,
) -> dict[str, Any]:
    if policy == "contact_tracing":
        return evaluate_contact_tracing(
            state=state,
            current_cases=current_state.get("infected", {}).get(state, 100),
            current_Rt=current_state.get("Rt_estimates", {}).get(state, 1.0),
            population=current_state.get("population", {}).get(state),
            variant=variant,
            projection_days=projection_days,
        )

    return {"success": False, "error": f"Policy {policy} not implemented yet"}
