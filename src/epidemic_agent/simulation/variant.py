from __future__ import annotations

import copy
import logging
from dataclasses import dataclass

import numpy as np
import pandas as pd
from scipy.integrate import solve_ivp
from scipy.optimize import differential_evolution, minimize

from ..config import VARIANT_PARAMS

logger = logging.getLogger(__name__)


@dataclass
class VariantParams:
    R0: float
    IFR: float
    immune_escape: float
    serial_interval: float
    name: str = "unknown"
    contact_rate_reduction: float = 0.0
    initial_recovered_frac: float = 0.0


class VariantParameterLearner:
    def __init__(self):
        self.known_variants = copy.deepcopy(VARIANT_PARAMS)
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

        daily_cases = cases.diff().fillna(0).clip(lower=0).values.astype(float)
        daily_deaths = deaths.diff().fillna(0).clip(lower=0).values.astype(float)
        cumulative_cases = cases.values.astype(float)
        cumulative_deaths = deaths.values.astype(float)

        if vaccination is not None:
            vax_rate = vaccination.values.astype(float) / population
        else:
            vax_rate = np.zeros(len(cases))

        days = len(cases)

        recent_cases = daily_cases[:14] if len(daily_cases) >= 14 else daily_cases
        initial_infected = max(int(np.median(recent_cases[recent_cases > 0])) if np.any(recent_cases > 0) else 100, 10)
        initial_infected = min(initial_infected, population // 1000)

        bounds = [
            (1.5, 8.0),
            (0.00005, 0.05),
            (0.0, 0.5),
            (2.0, 8.0),
            (0.0, 0.8),
            (0.0, 0.5),
        ]

        def objective(params):
            R0, IFR, immune_escape, serial_interval, contact_reduction, init_recovered = params
            if IFR * population < 1:
                return 1e10
            if R0 / serial_interval > 2.0:
                return 1e10

            simulated = self._simulate_seir_with_interventions(
                R0, IFR, immune_escape, serial_interval,
                contact_reduction, init_recovered,
                population, initial_infected, days, vax_rate,
            )
            sim_cases = simulated["daily_cases"]
            sim_deaths = simulated["daily_deaths"]
            sim_cum_cases = simulated["cumulative_cases"]
            sim_cum_deaths = simulated["cumulative_deaths"]

            real_daily_smooth = self._smooth(daily_cases, 7)
            sim_daily_smooth = self._smooth(sim_cases, 7)

            case_scale = max(np.percentile(real_daily_smooth[real_daily_smooth > 0], 50) if np.any(real_daily_smooth > 0) else 1, 1)
            death_scale = max(np.percentile(daily_deaths[daily_deaths > 0], 50) if np.any(daily_deaths > 0) else 1, 1)

            diff_cases = sim_daily_smooth - real_daily_smooth
            daily_case_err = np.mean(np.where(
                diff_cases > 0,
                (diff_cases / case_scale) ** 2 * 3.0,
                (diff_cases / case_scale) ** 2
            ))

            diff_deaths = sim_deaths - daily_deaths
            daily_death_err = np.mean(np.where(
                diff_deaths > 0,
                (diff_deaths / death_scale) ** 2 * 3.0,
                (diff_deaths / death_scale) ** 2
            ))

            cum_scale = max(cumulative_cases[-1], 1)
            cum_diff = sim_cum_cases[-1] - cumulative_cases[-1]
            cum_case_err = (cum_diff / cum_scale) ** 2 * (3.0 if cum_diff > 0 else 1.0)

            cum_d_scale = max(cumulative_deaths[-1], 1)
            cum_d_diff = sim_cum_deaths[-1] - cumulative_deaths[-1]
            cum_death_err = (cum_d_diff / cum_d_scale) ** 2 * (3.0 if cum_d_diff > 0 else 1.0)

            peak_real = np.max(real_daily_smooth) if np.any(real_daily_smooth > 0) else 1
            peak_sim = np.max(sim_daily_smooth) if np.any(sim_daily_smooth > 0) else 1
            peak_diff = peak_sim - peak_real
            peak_err = (peak_diff / max(peak_real, 1)) ** 2 * (3.0 if peak_diff > 0 else 1.0)

            peak_day_real = int(np.argmax(real_daily_smooth))
            peak_day_sim = int(np.argmax(sim_daily_smooth))
            timing_err = ((peak_day_sim - peak_day_real) / max(days, 1)) ** 2

            sim_attack_rate = sim_cum_cases[-1] / population
            real_attack_rate = cumulative_cases[-1] / population
            attack_rate_err = max(0, sim_attack_rate - real_attack_rate * 2.0) ** 2 * 10.0

            return (
                1.0 * daily_case_err
                + 5.0 * daily_death_err
                + 2.0 * cum_case_err
                + 5.0 * cum_death_err
                + 2.0 * peak_err
                + 1.0 * timing_err
                + 5.0 * attack_rate_err
            )

        result = differential_evolution(
            objective,
            bounds,
            seed=42,
            maxiter=200,
            tol=1e-8,
            popsize=15,
            mutation=(0.5, 1.0),
            recombination=0.7,
            polish=True,
        )

        if result.success or result.fun < 1e8:
            R0, IFR, immune_escape, serial_interval, contact_reduction, init_recovered = result.x
            logger.info(
                f"Optimization converged: R0={R0:.2f}, IFR={IFR:.5f}, "
                f"escape={immune_escape:.2f}, serial={serial_interval:.1f}, "
                f"contact_red={contact_reduction:.2f}, init_rec={init_recovered:.2f}, "
                f"loss={result.fun:.4f}"
            )
        else:
            logger.warning(f"Optimization failed: {result.message}")
            R0, IFR, immune_escape, serial_interval, contact_reduction, init_recovered = bounds[0][0], 0.005, 0.0, 5.0, 0.0, 0.0

        learned = VariantParams(
            R0=float(R0),
            IFR=float(IFR),
            immune_escape=float(immune_escape),
            serial_interval=float(serial_interval),
            contact_rate_reduction=float(contact_reduction),
            initial_recovered_frac=float(init_recovered),
            name=f"learned_{len(self.learned_variants)}",
        )

        self.learned_variants[learned.name] = learned

        logger.info(
            f"Learned variant params: R0={R0:.2f}, IFR={IFR:.5f}, "
            f"escape={immune_escape:.2f}, serial={serial_interval:.1f}, "
            f"contact_red={contact_reduction:.2f}, init_rec={init_recovered:.2f}"
        )
        return learned

    def _simulate_seir_with_interventions(
        self,
        R0: float,
        IFR: float,
        immune_escape: float,
        serial_interval: float,
        contact_reduction: float,
        init_recovered_frac: float,
        population: int,
        initial_infected: int,
        days: int,
        vax_rate: np.ndarray,
    ) -> dict[str, np.ndarray]:
        beta0 = R0 / serial_interval
        sigma = 1.0 / 5.2
        gamma = 1.0 / 7.0

        R0_init = int(population * init_recovered_frac)
        I0 = initial_infected
        E0 = initial_infected // 2
        S0 = population - E0 - I0 - R0_init
        D0 = 0

        t_span = (0, days)
        t_eval = np.arange(0, days, 0.1)

        def seir_ode(t, y):
            S, E, I, R, D = y
            N = S + E + I + R + D
            if N <= 0:
                return [0, 0, 0, 0, 0]

            day_idx = min(int(t), days - 1)

            vax_cumulative = float(np.sum(vax_rate[:day_idx + 1])) if day_idx < len(vax_rate) else 0
            vax_protection = min(vax_cumulative * 0.7 * (1 - immune_escape), 0.8)

            time_fraction = t / max(days, 1)
            intervention_effect = contact_reduction * (1 - np.exp(-3 * time_fraction))

            prevalence_frac = I / N if N > 0 else 0
            behavior_sensitivity = 50.0
            adaptive_behavior = prevalence_frac * behavior_sensitivity
            adaptive_factor = 1.0 / (1.0 + adaptive_behavior)

            effective_beta = beta0 * (1 - vax_protection) * (1 - intervention_effect) * adaptive_factor
            effective_beta = min(effective_beta, beta0)

            new_infections = effective_beta * S * I / N
            new_exposed = sigma * E
            new_infectious = gamma * I

            avg_IFR = IFR
            new_deaths = avg_IFR * new_infectious

            dS = -new_infections
            dE = new_infections - new_exposed
            dI = new_exposed - new_infectious
            dR = new_infectious - new_deaths
            dD = new_deaths

            return [dS, dE, dI, dR, dD]

        y0 = [S0, E0, I0, R0_init, D0]
        solution = solve_ivp(
            seir_ode,
            t_span,
            y0,
            t_eval=t_eval,
            method="RK45",
            rtol=1e-6,
            atol=1e-8,
        )

        S, E, I, R, D = solution.y
        t = solution.t

        daily_cases = np.zeros(days)
        daily_deaths = np.zeros(days)

        for i in range(days):
            mask = (t >= i) & (t < i + 1)
            if np.any(mask):
                idx = np.where(mask)[0]
                if len(idx) > 1:
                    daily_cases[i] = max(0, R[idx[-1]] + D[idx[-1]] - (R[idx[0]] + D[idx[0]]))
                    daily_deaths[i] = max(0, D[idx[-1]] - D[idx[0]])
                else:
                    daily_cases[i] = max(0, R[idx[0]] + D[idx[0]] - (R[max(0, idx[0]-1)] + D[max(0, idx[0]-1)]))
                    daily_deaths[i] = max(0, D[idx[0]] - D[max(0, idx[0]-1)])

        cumulative_cases = np.cumsum(daily_cases)
        cumulative_deaths = np.cumsum(daily_deaths)

        Rt = np.zeros(days)
        for i in range(days):
            N_i = S[i] + E[i] + I[i] + R[i]
            if I[i] > 1 and N_i > 0:
                Rt[i] = R0 * S[i] / N_i
            else:
                Rt[i] = R0 * max(S[i] / max(N_i, 1), 0.01)

        return {
            "daily_cases": daily_cases,
            "daily_deaths": daily_deaths,
            "cumulative_cases": cumulative_cases,
            "cumulative_deaths": cumulative_deaths,
            "Rt": Rt,
            "S": S,
            "E": E,
            "I": I,
            "R": R,
            "D": D,
        }

    @staticmethod
    def _smooth(arr: np.ndarray, window: int) -> np.ndarray:
        if len(arr) < window:
            return arr
        kernel = np.ones(window) / window
        return np.convolve(arr, kernel, mode="same")

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
