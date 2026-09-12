from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

import numpy as np

from ..config import VARIANT_PARAMS
from ..simulation.seir_model import SEIRModel

logger = logging.getLogger(__name__)


@dataclass
class SensitivityResult:
    parameter: str
    base_value: float
    variation_range: list[float]
    output_metric: str
    sensitivities: list[float]
    elasticity: float = 0.0
    rank_correlation: float = 0.0


@dataclass
class SensitivityAnalysis:
    results: list[SensitivityResult] = field(default_factory=list)
    parameter_importance: dict[str, float] = field(default_factory=dict)

    def summary(self) -> dict[str, Any]:
        return {
            "parameter_importance": self.parameter_importance,
            "most_important": max(self.parameter_importance, key=self.parameter_importance.get) if self.parameter_importance else "none",
            "details": [
                {
                    "parameter": r.parameter,
                    "base_value": r.base_value,
                    "elasticity": round(r.elasticity, 4),
                    "rank_correlation": round(r.rank_correlation, 4),
                }
                for r in self.results
            ],
        }


class SensitivityAnalyzer:
    def __init__(
        self,
        population: int = 124_000_000,
        variant: str = "wildtype",
        days: int = 90,
        initial_infected: int = 100,
    ):
        self.population = population
        self.variant = variant
        self.days = days
        self.initial_infected = initial_infected
        self.variant_params = VARIANT_PARAMS.get(variant, VARIANT_PARAMS["wildtype"])

    def _run_simulation(self, **overrides) -> dict[str, Any]:
        params = {
            "population": self.population,
            "R0": self.variant_params["R0"],
            "IFR": self.variant_params["IFR"],
            "immune_escape": self.variant_params["immune_escape"],
            "serial_interval": self.variant_params["serial_interval"],
            "incubation_period": 5.2,
            "infectious_period": 7.0,
            "days": self.days,
            "states": ["test"],
            "initial_infected": self.initial_infected,
        }
        params.update(overrides)

        model = SEIRModel(**params)
        result = model.run()

        daily_cases = np.array(result.daily_cases.get("test", [0] * self.days))
        daily_deaths = np.array(result.daily_deaths.get("test", [0] * self.days))

        return {
            "total_cases": float(np.sum(daily_cases)),
            "total_deaths": float(np.sum(daily_deaths)),
            "peak_cases": float(np.max(daily_cases)),
            "peak_day": int(np.argmax(daily_cases)),
            "final_Rt": float(result.daily_Rt.get("test", [1.0])[-1]),
        }

    def analyze_parameter(
        self,
        param_name: str,
        base_value: float,
        variations: list[float],
        output_metric: str = "total_deaths",
    ) -> SensitivityResult:
        base_output = self._run_simulation(**{param_name: base_value})
        base_val = base_output[output_metric]

        outputs = []
        for v in variations:
            result = self._run_simulation(**{param_name: v})
            outputs.append(result[output_metric])

        outputs = np.array(outputs)
        variations_arr = np.array(variations)

        sensitivities = []
        for i, v in enumerate(variations):
            if base_val > 0 and base_value > 0:
                s = (outputs[i] - base_val) / base_val / ((v - base_value) / base_value)
                sensitivities.append(float(s))
            else:
                sensitivities.append(0.0)

        valid_sens = [s for s in sensitivities if np.isfinite(s)]
        elasticity = float(np.mean(valid_sens)) if valid_sens else 0.0

        if len(variations) > 2:
            rank_corr = float(np.corrcoef(variations_arr, outputs)[0, 1])
        else:
            rank_corr = 0.0

        return SensitivityResult(
            parameter=param_name,
            base_value=base_value,
            variation_range=variations,
            output_metric=output_metric,
            sensitivities=sensitivities,
            elasticity=elasticity,
            rank_correlation=rank_corr,
        )

    def run_full_analysis(self) -> SensitivityAnalysis:
        parameters = {
            "R0": {
                "base": self.variant_params["R0"],
                "variations": [1.5, 2.0, 2.5, 3.0, 4.0, 5.0, 7.0, 10.0],
            },
            "IFR": {
                "base": self.variant_params["IFR"],
                "variations": [0.001, 0.003, 0.005, 0.01, 0.015, 0.02, 0.03],
            },
            "serial_interval": {
                "base": self.variant_params["serial_interval"],
                "variations": [2.0, 3.0, 4.0, 5.0, 6.0, 7.0],
            },
            "incubation_period": {
                "base": 5.2,
                "variations": [3.0, 4.0, 5.0, 6.0, 7.0, 8.0],
            },
            "infectious_period": {
                "base": 7.0,
                "variations": [5.0, 6.0, 7.0, 8.0, 9.0, 10.0],
            },
        }

        results = []
        for param_name, config in parameters.items():
            result = self.analyze_parameter(
                param_name=param_name,
                base_value=config["base"],
                variations=config["variations"],
                output_metric="total_deaths",
            )
            results.append(result)

        importance = {}
        max_abs_elasticity = max(abs(r.elasticity) for r in results) if results else 1.0
        for r in results:
            importance[r.parameter] = round(abs(r.elasticity) / max(max_abs_elasticity, 1e-10), 4)

        return SensitivityAnalysis(results=results, parameter_importance=importance)
