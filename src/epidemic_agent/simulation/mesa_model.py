from __future__ import annotations

import logging
from collections import defaultdict

import numpy as np
from mesa import Agent, Model
from mesa.space import MultiGrid

from ..config import (
    AGE_GROUPS,
    AGE_IFR_MULTIPLIER,
    COMORBIDITY_IFR_MULTIPLIER,
    get_state_population,
)
from ..simulation.result import SimulationResult

logger = logging.getLogger(__name__)


class PersonAgent(Agent):
    def __init__(
        self,
        model: EpidemicModel,
        state: str,
        district: str,
        age_group: str,
        has_comorbidity: bool,
    ):
        super().__init__(model)
        self.state_name = state
        self.district = district
        self.age_group = age_group
        self.has_comorbidity = has_comorbidity

        self.status: str = "susceptible"
        self.days_infected = 0
        self.vaccinated = False
        self.vaccine_efficacy = 0.0
        self.traced = False
        self.isolated = False
        self.contacts_traced = False
        self.traced_day = -1

    def step(self):
        if self.status == "exposed":
            self.days_infected += 1
            if self.days_infected >= self.model.incubation_period:
                self.status = "infected"
                self.days_infected = 0

        elif self.status == "infected":
            self.days_infected += 1

            if not self.isolated:
                self._spread_disease()

            if self.days_infected >= self.model.infectious_period:
                self._resolve_infection()

    def _spread_disease(self):
        cellmates = self.model.grid.get_cell_list_contents([self.pos])
        susceptible_neighbors = [a for a in cellmates if a.status == "susceptible"]

        if not susceptible_neighbors:
            return

        n_contacts = min(len(susceptible_neighbors), self.model.contacts_per_day)
        contacts = self.model.random.sample(susceptible_neighbors, n_contacts)

        for neighbor in contacts:
            if neighbor.vaccinated:
                infection_prob = self.model.transmission_prob * (1 - neighbor.vaccine_efficacy)
            else:
                infection_prob = self.model.transmission_prob

            if self.model.random.random() < infection_prob:
                neighbor.status = "exposed"
                neighbor.days_infected = 0
                self.model.new_infections_today += 1
                self.model._state_infections_today[neighbor.state_name] += 1

    def _resolve_infection(self):
        ifr = self.model.base_IFR * AGE_IFR_MULTIPLIER.get(self.age_group, 1.0)
        if self.has_comorbidity:
            ifr *= COMORBIDITY_IFR_MULTIPLIER

        if self.vaccinated:
            ifr *= (1 - self.vaccine_efficacy)

        if self.model.random.random() < ifr:
            self.status = "deceased"
            self.model.deaths_today += 1
            self.model._state_deaths_today[self.state_name] += 1
        else:
            self.status = "recovered"
            self.model.recoveries_today += 1


class EpidemicModel(Model):
    def __init__(
        self,
        population: int,
        R0: float,
        IFR: float,
        immune_escape: float,
        serial_interval: float,
        incubation_period: float,
        infectious_period: float,
        days: int,
        states: list[str],
        initial_infected: int = 100,
        contact_tracing_enabled: bool = False,
        tracing_efficiency: float = 0.6,
        isolation_compliance: float = 0.7,
        tracing_delay: int = 2,
        lockdown_reduction: float = 0.0,
        mask_reduction: float = 0.0,
        vaccination_rate_multiplier: float = 1.0,
        variant: str = "wildtype",
        random_seed: int = 42,
    ):
        super().__init__(seed=random_seed)

        population = max(1, int(population))
        R0 = max(0.01, float(R0))
        IFR = max(0.0, min(1.0, float(IFR)))
        days = max(1, int(days))
        initial_infected = max(0, min(initial_infected, population))

        self.population = population
        self.R0 = R0
        self.base_IFR = IFR
        self.immune_escape = max(0.0, min(1.0, float(immune_escape)))
        self.serial_interval = max(1.0, float(serial_interval))
        self.incubation_period = max(1, int(incubation_period))
        self.infectious_period = max(1, int(infectious_period))
        self.days = days
        self.states = states
        self.variant = variant

        self.contact_tracing_enabled = contact_tracing_enabled
        self.tracing_efficiency = max(0.0, min(1.0, float(tracing_efficiency)))
        self.isolation_compliance = max(0.0, min(1.0, float(isolation_compliance)))
        self.tracing_delay = max(0, int(tracing_delay))
        self.lockdown_reduction = max(0.0, min(1.0, float(lockdown_reduction)))
        self.mask_reduction = max(0.0, min(1.0, float(mask_reduction)))
        self.vaccination_rate_multiplier = max(0.0, float(vaccination_rate_multiplier))

        grid_size = max(10, int(np.sqrt(population / 50)))
        self.grid = MultiGrid(grid_size, grid_size, torus=True)

        self.contacts_per_day = max(1, int(np.sqrt(grid_size)))

        effective_R0 = R0
        effective_R0 *= (1 - self.lockdown_reduction)
        effective_R0 *= (1 - self.mask_reduction)
        self.transmission_prob = effective_R0 / (self.infectious_period * self.contacts_per_day)
        self.transmission_prob = max(0.0, min(1.0, self.transmission_prob))

        self.new_infections_today = 0
        self.deaths_today = 0
        self.recoveries_today = 0

        self._state_infections_today: dict[str, int] = defaultdict(int)
        self._state_deaths_today: dict[str, int] = defaultdict(int)

        self.daily_cases: dict[str, list[int]] = defaultdict(list)
        self.daily_deaths: dict[str, list[int]] = defaultdict(list)
        self.daily_Rt: dict[str, list[float]] = defaultdict(list)
        self.cumulative_cases: dict[str, list[int]] = defaultdict(list)
        self.cumulative_deaths: dict[str, list[int]] = defaultdict(list)
        self.variant_trajectory: dict[str, list[str]] = defaultdict(list)

        self._create_agents(initial_infected)
        self._initialize_vaccination()

    def _create_agents(self, initial_infected: int):
        state_pops = {s: get_state_population(s) for s in self.states}
        total_pop = sum(state_pops.values())

        raw = {s: state_pops[s] / total_pop * self.population for s in self.states}
        agents_per_state = {s: int(v) for s, v in raw.items()}
        remainder = self.population - sum(agents_per_state.values())
        if remainder > 0:
            largest = max(agents_per_state, key=agents_per_state.get)
            agents_per_state[largest] += remainder

        infected_assigned = 0
        all_agents = []

        for state, count in agents_per_state.items():
            districts = [f"{state}_D{i}" for i in range(max(1, count // 50000))]

            for _ in range(count):
                district = self.random.choice(districts)
                age_group = self.random.choices(AGE_GROUPS, weights=[12, 17, 18, 15, 12, 10, 8, 5, 3])[0]
                has_comorbidity = self.random.random() < 0.25

                agent = PersonAgent(self, state, district, age_group, has_comorbidity)

                x = self.random.randrange(self.grid.width)
                y = self.random.randrange(self.grid.height)
                self.grid.place_agent(agent, (x, y))
                all_agents.append(agent)

        if initial_infected > 0 and all_agents:
            n_infected = min(initial_infected, len(all_agents))
            infected_agents = self.random.sample(all_agents, n_infected)
            for agent in infected_agents:
                agent.status = "infected"
                agent.days_infected = self.random.randint(0, max(0, self.infectious_period - 1))
                infected_assigned += 1

        logger.info(f"Created agents across {len(self.states)} states, {infected_assigned} initially infected")

    def _initialize_vaccination(self):
        for agent in self.agents:
            if self.random.random() < 0.3 * self.vaccination_rate_multiplier:
                agent.vaccinated = True
                agent.vaccine_efficacy = 0.7 * (1 - self.immune_escape)

    def step(self):
        self.new_infections_today = 0
        self.deaths_today = 0
        self.recoveries_today = 0

        self._state_infections_today = defaultdict(int)
        self._state_deaths_today = defaultdict(int)

        self.agents.do("step")

        if self.contact_tracing_enabled and self.new_infections_today > 0:
            self._perform_contact_tracing()

        for state in self.states:
            state_infections = self._state_infections_today[state]
            state_deaths = self._state_deaths_today[state]

            self.daily_cases[state].append(state_infections)
            self.daily_deaths[state].append(state_deaths)
            prev_cum = self.cumulative_cases[state][-1] if self.cumulative_cases[state] else 0
            self.cumulative_cases[state].append(prev_cum + state_infections)
            prev_deaths = self.cumulative_deaths[state][-1] if self.cumulative_deaths[state] else 0
            self.cumulative_deaths[state].append(prev_deaths + state_deaths)

            if len(self.daily_cases[state]) >= 14:
                recent_avg = np.mean(self.daily_cases[state][-7:])
                prev_avg = np.mean(self.daily_cases[state][-14:-7])
                if prev_avg > 0 and recent_avg > 0:
                    growth_rate = np.log(recent_avg / prev_avg) / 7.0
                    Rt = 1.0 + growth_rate * self.serial_interval
                elif prev_avg > 0:
                    Rt = 0.5
                else:
                    Rt = self.R0
            elif len(self.daily_cases[state]) > 1:
                prev_state_cases = self.daily_cases[state][-2]
                if prev_state_cases > 0 and state_infections > 0:
                    daily_growth = np.log(state_infections / max(prev_state_cases, 1))
                    Rt = 1.0 + daily_growth * self.serial_interval
                else:
                    Rt = self.R0
            else:
                Rt = self.R0
            Rt = max(0.01, min(Rt, 15.0))
            self.daily_Rt[state].append(Rt)
            self.variant_trajectory[state].append(self.variant)

    def _perform_contact_tracing(self):
        current_day = len(self.daily_cases[self.states[0]]) if self.states else 0

        for agent in list(self.agents):
            if agent.traced and not agent.isolated and agent.traced_day >= 0:
                if current_day - agent.traced_day >= self.tracing_delay:
                    if self.random.random() < self.isolation_compliance:
                        agent.isolated = True

        infected_agents = [a for a in self.agents if a.status == "infected" and not a.contacts_traced]

        for agent in infected_agents:
            if self.random.random() > self.tracing_efficiency:
                continue

            cellmates = self.grid.get_cell_list_contents([agent.pos])
            contacts = [a for a in cellmates if a.status in ("susceptible", "exposed")]

            for contact in contacts:
                if not contact.traced:
                    contact.traced = True
                    contact.traced_day = current_day

            agent.contacts_traced = True

    def run(self) -> SimulationResult:
        for day in range(self.days):
            self.step()

            if day % 10 == 0:
                logger.debug(f"Day {day}: {self.new_infections_today} new cases, {self.deaths_today} deaths")

        return self._compile_results()

    def _compile_results(self) -> SimulationResult:
        peak_day = {}
        peak_cases = {}
        total_deaths = {}
        final_infected = {}

        for state in self.states:
            cases = self.daily_cases[state]
            deaths = self.cumulative_deaths[state]

            peak_day[state] = int(np.argmax(cases)) if cases else 0
            peak_cases[state] = int(max(cases)) if cases else 0
            total_deaths[state] = int(deaths[-1]) if deaths else 0

            final_infected[state] = self.cumulative_cases[state][-1] if self.cumulative_cases[state] else 0

        return SimulationResult(
            daily_cases=dict(self.daily_cases),
            daily_deaths=dict(self.daily_deaths),
            daily_Rt=dict(self.daily_Rt),
            cumulative_cases=dict(self.cumulative_cases),
            cumulative_deaths=dict(self.cumulative_deaths),
            peak_day=peak_day,
            peak_cases=peak_cases,
            total_deaths=total_deaths,
            final_infected=final_infected,
            variant_trajectory=dict(self.variant_trajectory),
            metadata={
                "model": "mesa",
                "R0": self.R0,
                "IFR": self.base_IFR,
                "contact_tracing": self.contact_tracing_enabled,
                "tracing_efficiency": self.tracing_efficiency,
            },
        )


def run_mesa_simulation(**kwargs) -> SimulationResult:
    model = EpidemicModel(**kwargs)
    return model.run()
