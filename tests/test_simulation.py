import numpy as np

from epidemic_agent.simulation.mesa_model import EpidemicModel
from epidemic_agent.simulation.seir_model import SEIRModel, run_seir_simulation
from epidemic_agent.simulation.variant import VariantParameterLearner, VariantParams


class TestMesaModel:
    def test_model_creation(self):
        model = EpidemicModel(
            population=10000,
            R0=2.5,
            IFR=0.005,
            immune_escape=0.0,
            serial_interval=5.2,
            incubation_period=5.2,
            infectious_period=7.0,
            days=30,
            states=["Maharashtra"],
            initial_infected=10,
        )
        assert len(model.agents) > 0
        assert model.transmission_prob > 0

    def test_model_step(self):
        model = EpidemicModel(
            population=1000,
            R0=2.5,
            IFR=0.005,
            immune_escape=0.0,
            serial_interval=5.2,
            incubation_period=5.2,
            infectious_period=7.0,
            days=30,
            states=["Maharashtra"],
            initial_infected=5,
        )
        initial_infected = sum(1 for a in model.agents if a.status == "infected")
        model.step()
        assert model.new_infections_today >= 0

    def test_contact_tracing(self):
        model = EpidemicModel(
            population=1000,
            R0=2.5,
            IFR=0.005,
            immune_escape=0.0,
            serial_interval=5.2,
            incubation_period=5.2,
            infectious_period=7.0,
            days=30,
            states=["Maharashtra"],
            initial_infected=5,
            contact_tracing_enabled=True,
            tracing_efficiency=0.8,
            isolation_compliance=0.9,
        )
        assert model.contact_tracing_enabled is True


class TestSEIRModel:
    def test_seir_creation(self):
        model = SEIRModel(
            population=1_000_000,
            R0=2.5,
            IFR=0.005,
            immune_escape=0.0,
            serial_interval=5.2,
            incubation_period=5.2,
            infectious_period=7.0,
            days=60,
            states=["Maharashtra"],
        )
        assert model.beta > 0
        assert model.sigma > 0
        assert model.gamma > 0

    def test_seir_run(self):
        result = run_seir_simulation(
            population=1_000_000,
            R0=2.5,
            IFR=0.005,
            immune_escape=0.0,
            serial_interval=5.2,
            incubation_period=5.2,
            infectious_period=7.0,
            days=30,
            states=["Maharashtra"],
            initial_infected=100,
        )
        result_dict = result.to_dict()
        assert "daily_cases" in result_dict
        assert "Maharashtra" in result_dict["daily_cases"]
        assert len(result_dict["daily_cases"]["Maharashtra"]) == 30  # days data points from diff


class TestVariantLearner:
    def test_default_params(self):
        learner = VariantParameterLearner()
        params = learner._default_params()
        assert isinstance(params, VariantParams)
        assert params.R0 == 3.0

    def test_learn_from_wave(self):
        import pandas as pd
        np.random.seed(42)
        days = 60
        cases = pd.Series(np.cumsum(np.random.poisson(50, days)))
        deaths = pd.Series(np.cumsum(np.random.poisson(2, days)))

        learner = VariantParameterLearner()
        params = learner.learn_from_wave(cases, deaths, population=1_000_000)

        assert isinstance(params, VariantParams)
        assert params.R0 > 0
        assert params.IFR > 0
        assert 0 <= params.immune_escape <= 1
