from __future__ import annotations

import logging
from typing import Any, Literal

from ..config import (
    CONTACT_TRACING_PARAMS,
    INCUBATION_PERIOD,
    INFECTIOUS_PERIOD,
    get_variant_params,
    settings,
)
from ..simulation.mesa_model import run_mesa_simulation
from ..simulation.seir_model import run_seir_simulation
from .registry import register_tool

logger = logging.getLogger(__name__)


def _merge_intervention_params(interventions: list[str], base_params: dict[str, Any]) -> dict[str, Any]:
    params = base_params.copy()
    if "contact_tracing" in interventions:
        params.update({
            "contact_tracing_enabled": True,
            "tracing_efficiency": CONTACT_TRACING_PARAMS["tracing_efficiency"],
            "isolation_compliance": CONTACT_TRACING_PARAMS["isolation_compliance"],
            "tracing_delay": CONTACT_TRACING_PARAMS["delay_days"],
        })
    if "lockdown" in interventions:
        params["lockdown_reduction"] = 0.6
    if "mask_mandate" in interventions:
        params["mask_reduction"] = 0.3
    if "vaccination_drive" in interventions:
        params["vaccination_rate_multiplier"] = 2.0
    if "travel_restrictions" in interventions:
        params["lockdown_reduction"] = max(params.get("lockdown_reduction", 0), 0.2)
    if "social_distancing" in interventions:
        params["mask_reduction"] = max(params.get("mask_reduction", 0), 0.15)
    if "quarantine" in interventions:
        params["isolation_compliance"] = max(params.get("isolation_compliance", 0), 0.5)
    if "enhanced_testing" in interventions:
        params["tracing_efficiency"] = max(params.get("tracing_efficiency", 0), 0.7)
    return params


@register_tool(description="Run epidemic simulation using Mesa (agent-based) or SEIR (compartmental) model")
def simulate_spread(
    model_type: Literal["mesa", "seir"] = "mesa",
    states: list[str] = None,
    variant: str = "wildtype",
    days: int = 60,
    interventions: list[str] = None,
    initial_infected: int = 100,
    population: int = None,
) -> dict[str, Any]:
    states = states or ["Maharashtra", "Kerala", "Delhi"]
    interventions = interventions or ["contact_tracing"]
    population = population or settings.default_population
    population = min(population, settings.default_population)

    variant_params = get_variant_params(variant)
    base_params = {
        "R0": variant_params["R0"],
        "IFR": variant_params["IFR"],
        "immune_escape": variant_params["immune_escape"],
        "serial_interval": variant_params["serial_interval"],
        "incubation_period": INCUBATION_PERIOD,
        "infectious_period": INFECTIOUS_PERIOD,
        "population": population,
        "initial_infected": initial_infected,
        "days": days,
        "states": states,
    }

    params = _merge_intervention_params(interventions, base_params)

    logger.info(f"Running {model_type} simulation for {states} with variant {variant}")

    try:
        if model_type == "mesa":
            result = run_mesa_simulation(**params)
        else:
            result = run_seir_simulation(**params)

        return {"success": True, "result": result.to_dict(), "model": model_type}
    except Exception as e:
        logger.error(f"Simulation failed: {e}", exc_info=True)
        return {"success": False, "error": str(e), "model": model_type}
