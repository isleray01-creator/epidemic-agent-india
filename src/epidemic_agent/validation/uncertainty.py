from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

import numpy as np

from ..config import VARIANT_PARAMS
from ..simulation.seir_model import SEIRModel

logger = logging.getLogger(__name__)


@dataclass
class UncertaintyBand:
    lower: list[float] = field(default_factory=list)
    median: list[float] = field(default_factory=list)
    upper: list[float] = field(default_factory=list)
    confidence_level: float = 0.95


@dataclass
class UncertaintyResult:
    mean_deaths: float = 0.0
    std_deaths: float = 0.0
    ci_lower_deaths: float = 0.0
    ci_upper_deaths: float = 0.0
    mean_peak_cases: float = 0.0
    std_peak_cases: float = 0.0
    mean_peak_day: float = 0.0
    std_peak_day: float = 0.0
    confidence_score: float = 0.0
    n_simulations: int = 0
    daily_cases_band: UncertaintyBand = field(default_factory=UncertaintyBand)
    daily_deaths_band: UncertaintyBand = field(default_factory=UncertaintyBand)

    def summary(self) -> dict[str, Any]:
        return {
            "mean_deaths": round(self.mean_deaths, 0),
            "std_deaths": round(self.std_deaths, 0),
            "95%_CI_deaths": f"[{self.ci_lower_deaths:,.0f}, {self.ci_upper_deaths:,.0f}]",
            "mean_peak_cases": round(self.mean_peak_cases, 0),
            "std_peak_cases": round(self.std_peak_cases, 0),
            "mean_peak_day": round(self.mean_peak_day, 1),
            "std_peak_day": round(self.std_peak_day, 1),
            "confidence_score": round(self.confidence_score, 3),
            "n_simulations": self.n_simulations,
        }


class UncertaintyQuantifier:
    def __init__(
        self,
        population: int = 124_000_000,
        variant: str = "wildtype",
        days: int = 90,
        initial_infected: int = 100,
        n_simulations: int = 100,
    ):
        self.population = population
        self.variant = variant
        self.days = days
        self.initial_infected = initial_infected
        self.n_simulations = n_simulations
        self.variant_params = VARIANT_PARAMS.get(variant, VARIANT_PARAMS["wildtype"])

    def _perturb_params(self, rng: np.random.Generator) -> dict[str, Any]:
        R0 = self.variant_params["R0"]
        IFR = self.variant_params["IFR"]
        immune_escape = self.variant_params["immune_escape"]
        serial_interval = self.variant_params["serial_interval"]

        R0_perturbed = rng.normal(R0, R0 * 0.2)
        R0_perturbed = max(1.0, min(R0_perturbed, 20.0))

        IFR_perturbed = rng.normal(IFR, IFR * 0.3)
        IFR_perturbed = max(0.0001, min(IFR_perturbed, 0.1))

        serial_perturbed = rng.normal(serial_interval, serial_interval * 0.15)
        serial_perturbed = max(1.5, min(serial_perturbed, 10.0))

        immune_perturbed = rng.normal(immune_escape, 0.1)
        immune_perturbed = max(0.0, min(immune_perturbed, 1.0))

        initial_perturbed = int(self.initial_infected * rng.normal(1.0, 0.3))
        initial_perturbed = max(10, min(initial_perturbed, self.population // 100))

        return {
            "population": self.population,
            "R0": R0_perturbed,
            "IFR": IFR_perturbed,
            "immune_escape": immune_perturbed,
            "serial_interval": serial_perturbed,
            "incubation_period": 5.2,
            "infectious_period": 7.0,
            "days": self.days,
            "states": ["test"],
            "initial_infected": initial_perturbed,
        }

    def quantify(self) -> UncertaintyResult:
        rng = np.random.default_rng(42)

        all_daily_cases = []
        all_daily_deaths = []
        all_total_deaths = []
        all_peak_cases = []
        all_peak_days = []

        for i in range(self.n_simulations):
            params = self._perturb_params(rng)
            try:
                model = SEIRModel(**params)
                result = model.run()

                daily_cases = np.array(result.daily_cases.get("test", [0] * self.days))
                daily_deaths = np.array(result.daily_deaths.get("test", [0] * self.days))

                all_daily_cases.append(daily_cases)
                all_daily_deaths.append(daily_deaths)
                all_total_deaths.append(float(np.sum(daily_deaths)))
                all_peak_cases.append(float(np.max(daily_cases)))
                all_peak_days.append(float(np.argmax(daily_cases)))
            except Exception as e:
                logger.warning(f"Simulation {i} failed: {e}")

        if not all_total_deaths:
            return UncertaintyResult(n_simulations=0)

        cases_arr = np.array(all_daily_cases)
        deaths_arr = np.array(all_daily_deaths)
        total_deaths = np.array(all_total_deaths)
        peak_cases = np.array(all_peak_cases)
        peak_days = np.array(all_peak_days)

        alpha = (1 - 0.95) / 2

        cases_lower = np.percentile(cases_arr, alpha * 100, axis=0)
        cases_median = np.median(cases_arr, axis=0)
        cases_upper = np.percentile(cases_arr, (1 - alpha) * 100, axis=0)

        deaths_lower = np.percentile(deaths_arr, alpha * 100, axis=0)
        deaths_median = np.median(deaths_arr, axis=0)
        deaths_upper = np.percentile(deaths_arr, (1 - alpha) * 100, axis=0)

        mean_deaths = float(np.mean(total_deaths))
        std_deaths = float(np.std(total_deaths))
        ci_lower = float(np.percentile(total_deaths, alpha * 100))
        ci_upper = float(np.percentile(total_deaths, (1 - alpha) * 100))

        cv = std_deaths / max(mean_deaths, 1)
        confidence = max(0.0, min(1.0, 1.0 - cv))

        return UncertaintyResult(
            mean_deaths=mean_deaths,
            std_deaths=std_deaths,
            ci_lower_deaths=ci_lower,
            ci_upper_deaths=ci_upper,
            mean_peak_cases=float(np.mean(peak_cases)),
            std_peak_cases=float(np.std(peak_cases)),
            mean_peak_day=float(np.mean(peak_days)),
            std_peak_day=float(np.std(peak_days)),
            confidence_score=confidence,
            n_simulations=len(all_total_deaths),
            daily_cases_band=UncertaintyBand(
                lower=cases_lower.tolist(),
                median=cases_median.tolist(),
                upper=cases_upper.tolist(),
            ),
            daily_deaths_band=UncertaintyBand(
                lower=deaths_lower.tolist(),
                median=deaths_median.tolist(),
                upper=deaths_upper.tolist(),
            ),
        )
