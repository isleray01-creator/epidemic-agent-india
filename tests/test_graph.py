from unittest.mock import patch

import pytest

from epidemic_agent.graph import get_workflow
from epidemic_agent.state import EpidemicState


class TestWorkflow:
    @pytest.fixture
    def initial_state(self):
        return EpidemicState(
            current_day=0,
            simulation_days=14,
            country="India",
            states=["Maharashtra", "Kerala"],
            population={"Maharashtra": 124_000_000, "Kerala": 35_000_000},
            infected={"Maharashtra": 100, "Kerala": 50},
            exposed={"Maharashtra": 50, "Kerala": 25},
            recovered={"Maharashtra": 0, "Kerala": 0},
            deceased={"Maharashtra": 0, "Kerala": 0},
            vaccinated={"Maharashtra": 37_200_000, "Kerala": 10_500_000},
            active_variants={"Maharashtra": "wildtype", "Kerala": "wildtype"},
            variant_prevalence={"Maharashtra": {"wildtype": 1.0}, "Kerala": {"wildtype": 1.0}},
            current_policies={"Maharashtra": [], "Kerala": []},
            intervention_history=[],
            variant_shock=None,
            confidence_score=1.0,
            objective_value=0.0,
            objective_breakdown={},
            Rt_estimates={"Maharashtra": 2.5, "Kerala": 2.5},
            healthcare_capacity={},
            contact_tracing_metrics={},
            metadata={"adaptation_loops": 0},
        )

    @patch("epidemic_agent.graph.nodes.fetch_epidemic_data")
    @patch("epidemic_agent.graph.nodes.fetch_demographics")
    @patch("epidemic_agent.graph.nodes.simulate_spread")
    @patch("epidemic_agent.graph.nodes.detect_variant_shock")
    @patch("epidemic_agent.graph.nodes.evaluate_contact_tracing")
    @patch("epidemic_agent.graph.nodes.calculate_objective")
    def test_workflow_runs(
        self,
        mock_obj,
        mock_eval,
        mock_shock,
        mock_sim,
        mock_demo,
        mock_fetch,
        initial_state,
    ):
        mock_fetch.invoke.return_value = {"data": [], "states": ["Maharashtra", "Kerala"]}
        mock_demo.invoke.return_value = {"demographics": {}}
        mock_sim.invoke.return_value = {
            "success": True,
            "result": {
                "daily_cases": {"Maharashtra": [10]*14, "Kerala": [5]*14},
                "daily_deaths": {"Maharashtra": [1]*14, "Kerala": [0]*14},
                "daily_Rt": {"Maharashtra": [1.2]*14, "Kerala": [1.1]*14},
                "cumulative_cases": {"Maharashtra": list(range(10, 150, 10)), "Kerala": list(range(5, 75, 5))},
                "cumulative_deaths": {"Maharashtra": list(range(1, 15)), "Kerala": [0]*14},
                "peak_day": {"Maharashtra": 10, "Kerala": 8},
                "peak_cases": {"Maharashtra": 20, "Kerala": 10},
                "total_deaths": {"Maharashtra": 14, "Kerala": 0},
                "final_infected": {"Maharashtra": 140, "Kerala": 70},
                "variant_trajectory": {"Maharashtra": ["wildtype"]*14, "Kerala": ["wildtype"]*14},
                "metadata": {},
            },
        }
        mock_shock.invoke.return_value = {
            "shock_detected": False,
            "anomalies": {},
            "severity": "none",
            "recommended_action": "continue",
            "confidence": 1.0,
        }
        mock_eval.invoke.return_value = {
            "success": True,
            "evaluation": {
                "projected_cases": 100,
                "projected_deaths": 10,
                "projected_peak_day": 10,
                "projected_peak_cases": 20,
                "Rt_reduction": 0.3,
                "cost_inr": 500000,
                "cost_per_death_averted": 50000,
                "confidence": 0.75,
            },
        }
        mock_obj.invoke.return_value = {
            "total_objective": 0.15,
            "breakdown": {"deaths": 0.05, "economic_cost": 0.05, "social_cost": 0.03, "healthcare_strain": 0.02},
            "deaths": 10,
            "economic_cost": 500000,
            "social_cost": 5000,
            "healthcare_strain": 0.3,
        }

        workflow = get_workflow()
        result = workflow.run(initial_state)

        assert result["current_day"] > 0
        assert "final_recommendation" in result["metadata"]
