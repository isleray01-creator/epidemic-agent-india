from __future__ import annotations

import logging
from dataclasses import asdict, dataclass
from typing import Any

from ..config import OBJECTIVE_WEIGHTS
from .registry import register_tool

logger = logging.getLogger(__name__)


@dataclass
class ObjectiveResult:
    total_objective: float
    breakdown: dict[str, float]
    deaths: int
    economic_cost: float
    social_cost: float
    healthcare_strain: float


class ObjectiveFunction:
    def __init__(self, weights: dict[str, float] = None):
        self.weights = weights or OBJECTIVE_WEIGHTS.copy()

    def calculate(
        self,
        deaths: int,
        population: int,
        economic_cost: float,
        social_cost: float,
        icu_occupancy: float,
        max_icu_capacity: float,
    ) -> ObjectiveResult:
        death_score = min(deaths / max(population * 0.01, 1), 1.0)
        econ_score = min(economic_cost / max(population * 10000, 1), 1.0)
        social_score = min(social_cost / 100, 1.0)
        healthcare_score = min(icu_occupancy / max(max_icu_capacity, 1), 1.0)

        total = (
            self.weights["deaths"] * death_score +
            self.weights["economic_cost"] * econ_score +
            self.weights["social_cost"] * social_score +
            self.weights["healthcare_strain"] * healthcare_score
        )

        return ObjectiveResult(
            total_objective=total,
            breakdown={
                "deaths": self.weights["deaths"] * death_score,
                "economic_cost": self.weights["economic_cost"] * econ_score,
                "social_cost": self.weights["social_cost"] * social_score,
                "healthcare_strain": self.weights["healthcare_strain"] * healthcare_score,
            },
            deaths=deaths,
            economic_cost=economic_cost,
            social_cost=social_cost,
            healthcare_strain=healthcare_score,
        )


@register_tool(description="Calculate composite objective function value (lower is better)")
def calculate_objective(
    deaths: int,
    population: int,
    economic_cost: float,
    social_cost: float,
    healthcare_strain: float,
    weights: dict[str, float] = None,
) -> dict[str, Any]:
    obj_fn = ObjectiveFunction(weights)
    max_icu = population * 0.0005
    result = obj_fn.calculate(deaths, population, economic_cost, social_cost, healthcare_strain, max_icu)
    return asdict(result)
