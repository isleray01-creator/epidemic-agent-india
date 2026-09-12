from __future__ import annotations

import logging
from dataclasses import dataclass

import numpy as np
import pandas as pd
from scipy.optimize import minimize

from ..config import VARIANT_PARAMS

logger = logging.getLogger(__name__)


@dataclass
class VariantParams:
    R0: float
    IFR: float
    immune_escape: float
    serial_interval: float
    name: str = "unknown"


class VariantParameterLearner:
    def __init__(self):
        self.known_variants = VARIANT_PARAMS.copy()
        self.learned_variants: dict[str, VariantParams] = {}

    def learn_from_wave(
        self,
        cases: pd.Series,
        deaths: pd.Series,
        vaccination: pd.Series = None,
        population: int = 1_000_000,
        initial_guess: dict[str, float] = None,
    ) -> VariantParams:
        if len(cases) < 14:
            logger.warning("Insufficient data for variant learning (< 14 days)")
            return self._default_params()

        daily_cases = cases.diff().fillna(0).clip(lower=0).values
        daily_deaths = deaths.diff().fillna(0).clip(lower=0).values

        if vaccination is not None:
            vax_rate = vaccination.values / population
        else:
            vax_rate = np.zeros(len(cases))

        def objective(params):
            R0, IFR, immune_escape, serial_interval = params
            simulated = self._simulate_seir(
                R0, IFR, immune_escape, serial_interval,
                population, cases.iloc[0], len(cases), vax_rate
            )
            case_error = np.mean((simulated["daily_cases"] - daily_cases) ** 2)
            death_error = np.mean((simulated["daily_deaths"] - daily_deaths) ** 2)
            return case_error + 10 * death_error

        bounds = [
            (1.5, 15.0),
            (0.0001, 0.05),
            (0.0, 1.0),
            (2.0, 7.0),
        ]

        x0 = initial_guess or [3.0, 0.005, 0.0, 5.0]

        result = minimize(objective, x0, bounds=bounds, method="L-BFGS-B")

        if result.success:
            R0, IFR, immune_escape, serial_interval = result.x
        else:
            logger.warning(f"Optimization failed: {result.message}, using initial guess")
            R0, IFR, immune_escape, serial_interval = x0

        learned = VariantParams(
            R0=float(R0),
            IFR=float(IFR),
            immune_escape=float(immune_escape),
            serial_interval=float(serial_interval),
            name=f"learned_{len(self.learned_variants)}",
        )

        logger.info(
            f"Learned variant params: R0={R0:.2f}, IFR={IFR:.4f}, "
            f"escape={immune_escape:.2f}, serial={serial_interval:.1f}"
        )
        return learned

    def _simulate_seir(
        self,
        R0: float,
        IFR: float,
        immune_escape: float,
        serial_interval: float,
        population: int,
        initial_infected: int,
        days: int,
        vax_rate: np.ndarray,
    ) -> dict[str, np.ndarray]:
        beta = R0 / (serial_interval * 0.7)
        sigma = 1.0 / 5.2
        gamma = 1.0 / 7.0

        S = population - initial_infected
        E = initial_infected // 2
        I = initial_infected - E
        R = 0
        D = 0

        daily_cases = []
        daily_deaths = []

        for day in range(days):
            N = S + E + I + R
            if N == 0:
                daily_cases.append(0)
                daily_deaths.append(0)
                continue

            eff_beta = beta * (1 - vax_rate[day] * 0.7 * (1 - immune_escape))

            new_inf = eff_beta * S * I / N
            new_exp = new_inf
            new_infec = sigma * E
            new_rec = gamma * I

            avg_IFR = IFR * 1.5
            new_deaths = avg_IFR * new_rec

            S -= new_inf
            E += new_exp - new_infec
            I += new_infec - new_rec
            R += new_rec - new_deaths
            D += new_deaths

            daily_cases.append(new_inf)
            daily_deaths.append(new_deaths)

        return {
            "daily_cases": np.array(daily_cases),
            "daily_deaths": np.array(daily_deaths),
        }

    def _default_params(self) -> VariantParams:
        return VariantParams(R0=3.0, IFR=0.005, immune_escape=0.0, serial_interval=5.0, name="default")

    def match_known_variant(self, params: VariantParams) -> str:
        best_match = "unknown"
        min_distance = float("inf")

        for name, known in self.known_variants.items():
            distance = (
                abs(params.R0 - known["R0"]) / known["R0"] +
                abs(params.IFR - known["IFR"]) / max(known["IFR"], 0.001) +
                abs(params.immune_escape - known["immune_escape"]) +
                abs(params.serial_interval - known["serial_interval"]) / known["serial_interval"]
            )
            if distance < min_distance:
                min_distance = distance
                best_match = name

        if min_distance < 0.5:
            return best_match
        return "unknown"

    def get_variant_params(self, variant_name: str) -> VariantParams:
        if variant_name in self.known_variants:
            vp = self.known_variants[variant_name]
            return VariantParams(**vp, name=variant_name)

        if variant_name in self.learned_variants:
            return self.learned_variants[variant_name]

        return self._default_params()
