from __future__ import annotations

import logging
from dataclasses import dataclass

import numpy as np
from scipy.integrate import solve_ivp

from ..config import COMORBIDITY_IFR_MULTIPLIER
from ..simulation.result import SimulationResult

logger = logging.getLogger(__name__)


@dataclass
class SEIRModel:
    population: int
    R0: float
    IFR: float
    immune_escape: float
    serial_interval: float
    incubation_period: float
    infectious_period: float
    days: int
    states: list[str]
    initial_infected: int = 100
    contact_tracing_enabled: bool = False
    tracing_efficiency: float = 0.6
    isolation_compliance: float = 0.7
    tracing_delay: int = 2
    lockdown_reduction: float = 0.0
    mask_reduction: float = 0.0
    vaccination_rate_multiplier: float = 1.0
    variant: str = "wildtype"
    state_populations: dict[str, int] | None = None
    state_infected: dict[str, int] | None = None

    def __post_init__(self):
        self.beta = self.R0 / self.infectious_period
        self.sigma = 1.0 / self.incubation_period
        self.gamma = 1.0 / self.infectious_period

        if self.lockdown_reduction > 0:
            self.beta *= (1 - self.lockdown_reduction)
        if self.mask_reduction > 0:
            self.beta *= (1 - self.mask_reduction)

        self.vaccinated_fraction = 0.3 * self.vaccination_rate_multiplier
        self.vaccine_efficacy = 0.7 * (1 - self.immune_escape)

    def _seir_ode(self, t, y):
        S, E, I, R, D = y
        N = S + E + I + R + D

        if N == 0:
            return [0, 0, 0, 0, 0]

        effective_beta = self.beta
        if self.contact_tracing_enabled:
            traced_fraction = self.tracing_efficiency * self.isolation_compliance
            effective_beta *= (1 - traced_fraction)

        new_infections = effective_beta * S * I / N
        leaving_exposed = self.sigma * E
        leaving_infectious = self.gamma * I

        avg_IFR = self.IFR
        avg_IFR *= (1 - self.vaccinated_fraction * self.vaccine_efficacy)
        avg_IFR *= (1 + 0.25 * (COMORBIDITY_IFR_MULTIPLIER - 1))
        avg_IFR = min(avg_IFR, 1.0)

        new_deaths = avg_IFR * leaving_infectious
        new_recovered = leaving_infectious - new_deaths

        dS = -new_infections
        dE = new_infections - leaving_exposed
        dI = leaving_exposed - leaving_infectious
        dR = new_recovered
        dD = new_deaths

        return [dS, dE, dI, dR, dD]

    def _run_single_state(self, state_pop: int, state_infected: int) -> dict:
        S0 = state_pop - state_infected
        E0 = state_infected // 2
        I0 = state_infected - E0
        R_init = 0
        D0 = 0

        y0 = [S0, E0, I0, R_init, D0]
        t_span = (0, self.days)
        t_eval = np.arange(0, self.days + 1, 1)

        solution = solve_ivp(
            self._seir_ode,
            t_span,
            y0,
            t_eval=t_eval,
            method="RK45",
            rtol=1e-6,
            atol=1e-8,
        )

        S, E, I, R, D = solution.y

        daily_cases = np.maximum(-np.diff(S), 0)
        daily_deaths = np.maximum(np.diff(D), 0)

        Rt = []
        effective_beta = self.beta
        if self.contact_tracing_enabled:
            traced_fraction = self.tracing_efficiency * self.isolation_compliance
            effective_beta *= (1 - traced_fraction)
        for i in range(len(I)):
            N_i = S[i] + E[i] + I[i] + R[i] + D[i]
            if N_i > 0:
                Rt.append(effective_beta * S[i] / (self.gamma * N_i))
            else:
                Rt.append(1.0)

        cumulative_cases = np.cumsum(daily_cases)
        cumulative_deaths = np.cumsum(daily_deaths)

        peak_day = int(np.argmax(daily_cases)) if len(daily_cases) > 0 else 0
        peak_cases = int(np.max(daily_cases)) if len(daily_cases) > 0 else 0

        return {
            "daily_cases": daily_cases.tolist(),
            "daily_deaths": daily_deaths.tolist(),
            "daily_Rt": Rt,
            "cumulative_cases": cumulative_cases.tolist(),
            "cumulative_deaths": cumulative_deaths.tolist(),
            "peak_day": peak_day,
            "peak_cases": peak_cases,
            "total_deaths": int(D[-1]),
            "final_infected": int(state_pop - S[-1]),
            "variant_trajectory": [self.variant] * len(daily_cases),
        }

    def run(self) -> SimulationResult:
        n_states = len(self.states)
        total_pop = self.population
        total_infected = self.initial_infected

        state_results = {}

        for state_name in self.states:
            if self.state_populations and state_name in self.state_populations:
                state_pop = self.state_populations[state_name]
            else:
                state_pop = max(1, total_pop // n_states)

            if self.state_infected and state_name in self.state_infected:
                state_inf = self.state_infected[state_name]
            else:
                state_inf = max(1, total_infected // n_states)

            state_results[state_name] = self._run_single_state(state_pop, state_inf)

        return SimulationResult(
            daily_cases={s: r["daily_cases"] for s, r in state_results.items()},
            daily_deaths={s: r["daily_deaths"] for s, r in state_results.items()},
            daily_Rt={s: r["daily_Rt"] for s, r in state_results.items()},
            cumulative_cases={s: r["cumulative_cases"] for s, r in state_results.items()},
            cumulative_deaths={s: r["cumulative_deaths"] for s, r in state_results.items()},
            peak_day={s: r["peak_day"] for s, r in state_results.items()},
            peak_cases={s: r["peak_cases"] for s, r in state_results.items()},
            total_deaths={s: r["total_deaths"] for s, r in state_results.items()},
            final_infected={s: r["final_infected"] for s, r in state_results.items()},
            variant_trajectory={s: r["variant_trajectory"] for s, r in state_results.items()},
            metadata={
                "model": "seir",
                "R0": self.R0,
                "IFR": self.IFR,
                "contact_tracing": self.contact_tracing_enabled,
                "tracing_efficiency": self.tracing_efficiency,
            },
        )


def run_seir_simulation(**kwargs) -> SimulationResult:
    model = SEIRModel(**kwargs)
    return model.run()
