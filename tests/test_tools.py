from unittest.mock import MagicMock, patch

import pytest

from epidemic_agent.tools import (
    calculate_objective,
    detect_variant_shock,
    evaluate_contact_tracing,
    fetch_demographics,
    fetch_epidemic_data,
    simulate_spread,
)


class TestDataFetcher:
    @patch("epidemic_agent.tools.data_fetcher.requests.get")
    def test_fetch_epidemic_data(self, mock_get):
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "MH": {
                "2024-01-01": {
                    "total": {"confirmed": 1000, "deceased": 10, "recovered": 500, "tested": 5000},
                    "delta": {"confirmed": 50, "deceased": 1, "recovered": 20, "tested": 200},
                }
            }
        }
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        result = fetch_epidemic_data.invoke({"states": ["Maharashtra"], "days_back": 7})
        assert "data" in result
        assert len(result["data"]) > 0

    def test_fetch_demographics(self):
        result = fetch_demographics.invoke({"states": ["Maharashtra"]})
        assert "demographics" in result
        assert "Maharashtra" in result["demographics"]
        demo = result["demographics"]["Maharashtra"]
        assert "population" in demo
        assert "age_distribution" in demo
        assert "healthcare_capacity" in demo


class TestSimulator:
    def test_simulate_spread_mesa(self):
        result = simulate_spread.invoke({
            "model_type": "mesa",
            "states": ["Maharashtra"],
            "variant": "wildtype",
            "days": 14,
            "interventions": ["contact_tracing"],
        })
        assert "success" in result
        if result["success"]:
            assert "result" in result
            assert "daily_cases" in result["result"]

    def test_simulate_spread_seir(self):
        result = simulate_spread.invoke({
            "model_type": "seir",
            "states": ["Maharashtra"],
            "variant": "wildtype",
            "days": 14,
            "interventions": [],
        })
        assert "success" in result


class TestShockDetector:
    def test_no_shock(self):
        predicted = {"cases": 100, "deaths": 5, "Rt": 1.2}
        actual = {"cases": 105, "deaths": 5, "Rt": 1.25}

        result = detect_variant_shock.invoke({
            "predicted": predicted,
            "actual": actual,
            "threshold": 0.15,
        })

        assert result["shock_detected"] is False

    def test_shock_detected(self):
        predicted = {"cases": 100, "deaths": 5, "Rt": 1.2}
        actual = {"cases": 200, "deaths": 15, "Rt": 2.5}

        result = detect_variant_shock.invoke({
            "predicted": predicted,
            "actual": actual,
            "threshold": 0.15,
        })

        assert result["shock_detected"] is True
        assert "cases" in result["anomalies"]


class TestPolicyEval:
    def test_evaluate_contact_tracing(self):
        result = evaluate_contact_tracing.invoke({
            "state": "Maharashtra",
            "current_cases": 1000,
            "current_Rt": 1.5,
            "population": 124_000_000,
            "variant": "wildtype",
            "projection_days": 30,
        })

        assert "success" in result
        if result["success"]:
            eval_data = result["evaluation"]
            assert "projected_deaths" in eval_data
            assert "cost_inr" in eval_data
            assert "Rt_reduction" in eval_data


class TestObjective:
    def test_calculate_objective(self):
        result = calculate_objective.invoke({
            "deaths": 1000,
            "population": 1_000_000,
            "economic_cost": 10_000_000,
            "social_cost": 5000,
            "healthcare_strain": 0.3,
        })

        assert "total_objective" in result
        assert "breakdown" in result
        assert result["total_objective"] >= 0
        assert result["total_objective"] <= 1
        assert sum(result["breakdown"].values()) == pytest.approx(result["total_objective"], rel=1e-3)
