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

        initial_infected = max(int(daily_cases[0]) if len(daily_cases) > 0 else 100, 100)

        bounds = [
            (1.5, 15.0),
            (0.0001, 0.05),
            (0.0, 1.0),
            (2.0, 7.0),
        ]

        x0 = initial_guess or self._get_initial_guess(cases, deaths, population)

        case_weight = 1.0
        death_weight = 10.0

        def objective(params):
            R0, IFR, immune_escape, serial_interval = params
            simulated = self._simulate_seir(
                R0, IFR, immune_escape, serial_interval,
                population, initial_infected, len(cases), vax_rate
            )
            sim_cases = simulated["daily_cases"]
            sim_deaths = simulated["daily_deaths"]

            case_scale = max(np.mean(daily_cases), 1)
            death_scale = max(np.mean(daily_deaths), 1)

            case_error = np.mean(((sim_cases - daily_cases) / case_scale) ** 2)
            death_error = np.mean(((sim_deaths - daily_deaths) / death_scale) ** 2)

            return case_weight * case_error + death_weight * death_error

        result = minimize(objective, x0, bounds=bounds, method="L-BFGS-B",
                         options={"maxiter": 500, "ftol": 1e-10})

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
        beta = R0 / serial_interval
        sigma = 1.0 / 5.2
        gamma = 1.0 / 7.0

        I = initial_infected
        E = initial_infected // 2
        R = int(population * 0.3)
        S = population - I - E - R
        D = 0

        daily_cases = []
        daily_deaths = []

        for day in range(days):
            N = S + E + I + R
            if N <= 0:
                daily_cases.append(0)
                daily_deaths.append(0)
                continue

            vax_effect = 0.0
            if day < len(vax_rate) and vax_rate[day] > 0:
                vax_effect = vax_rate[day] * 0.7 * (1 - immune_escape)

            effective_beta = beta * (1 - vax_effect)

            new_inf = effective_beta * S * I / N
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

            S = max(S, 0)
            E = max(E, 0)
            I = max(I, 0)
            R = max(R, 0)

            daily_cases.append(new_inf)
            daily_deaths.append(new_deaths)

        return {
            "daily_cases": np.array(daily_cases),
            "daily_deaths": np.array(daily_deaths),
        }

    def _default_params(self) -> VariantParams:
        return VariantParams(R0=3.0, IFR=0.005, immune_escape=0.0, serial_interval=5.0, name="default")

    def _get_initial_guess(self, cases: pd.Series, deaths: pd.Series, population: int) -> list:
        daily_cases = cases.diff().fillna(0).clip(lower=0).values
        daily_deaths = deaths.diff().fillna(0).clip(lower=0).values

        peak_cases = float(np.max(daily_cases)) if len(daily_cases) > 0 else 100
        total_cases = float(np.sum(daily_cases))
        total_deaths = float(np.sum(daily_deaths))

        if total_cases > 0:
            crude_ifr = total_deaths / total_cases
            crude_ifr = max(0.0005, min(crude_ifr, 0.05))
        else:
            crude_ifr = 0.005

        if peak_cases > 0 and population > 0:
            rough_R0 = 2.0 + (peak_cases / population) * 1000
            rough_R0 = max(1.5, min(rough_R0, 12.0))
        else:
            rough_R0 = 3.0

        return [rough_R0, crude_ifr, 0.0, 4.5]

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
