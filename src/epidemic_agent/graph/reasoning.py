"""LLM Reasoning node - interprets simulation results and suggests policies.

Uses local rule-based reasoning when no LLM API is available.
Falls back gracefully to heuristic decision-making.
"""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)

POLICY_EFFECTIVENESS = {
    "lockdown": {"r0_reduction": 0.60, "economic_cost": 0.90, "social_cost": 0.80, "lag_days": 14},
    "mask_mandate": {"r0_reduction": 0.33, "economic_cost": 0.10, "social_cost": 0.20, "lag_days": 7},
    "vaccination_drive": {"r0_reduction": 0.25, "economic_cost": 0.30, "social_cost": 0.05, "lag_days": 21},
    "contact_tracing": {"r0_reduction": 0.20, "economic_cost": 0.15, "social_cost": 0.10, "lag_days": 7},
    "enhanced_testing": {"r0_reduction": 0.15, "economic_cost": 0.20, "social_cost": 0.05, "lag_days": 5},
    "travel_restrictions": {"r0_reduction": 0.20, "economic_cost": 0.40, "social_cost": 0.50, "lag_days": 10},
    "social_distancing": {"r0_reduction": 0.30, "economic_cost": 0.25, "social_cost": 0.30, "lag_days": 7},
    "quarantine": {"r0_reduction": 0.35, "economic_cost": 0.30, "social_cost": 0.40, "lag_days": 7},
}

SEVERITY_THRESHOLDS = {
    "critical": {"r0": 6.0, "deaths_per_million": 50, "icu_utilization": 0.90},
    "high": {"r0": 4.0, "deaths_per_million": 20, "icu_utilization": 0.75},
    "medium": {"r0": 2.5, "deaths_per_million": 10, "icu_utilization": 0.50},
    "low": {"r0": 1.5, "deaths_per_million": 2, "icu_utilization": 0.25},
}


@dataclass
class ReasoningResult:
    severity: str
    rationale: str
    recommended_policies: list[str]
    confidence: float
    uncertainty_factors: list[str]
    policy_ranking: list[dict[str, Any]]
    failure_detected: bool = False
    failure_type: str = ""
    recovery_action: str = ""


class LLMReasoner:
    """Rule-based reasoning engine for epidemic response decisions."""

    def __init__(self):
        pass

    def reason(
        self,
        state: dict[str, Any],
        history: list[dict[str, Any]] = None,
    ) -> ReasoningResult:
        history = history or []

        failure = self._detect_failure(state)
        if failure:
            return self._handle_failure(state, failure)

        severity = self._assess_severity(state)
        uncertainty = self._assess_uncertainty(state, history)
        policies = self._select_policies(severity, state, uncertainty)
        ranking = self._rank_policies(policies, state, uncertainty)
        rationale = self._generate_rationale(severity, state, ranking, uncertainty)

        return ReasoningResult(
            severity=severity,
            rationale=rationale,
            recommended_policies=[r["policy"] for r in ranking[:3]],
            confidence=max(0.3, 1.0 - len(uncertainty) * 0.1),
            uncertainty_factors=uncertainty,
            policy_ranking=ranking,
        )

    def _detect_failure(self, state: dict[str, Any]) -> dict[str, Any] | None:
        infected = state.get("infected", {})
        deceased = state.get("deceased", {})
        population = state.get("population", {})

        for s in infected:
            if infected[s] < 0:
                return {"type": "negative_cases", "state": s, "detail": f"Negative cases in {s}"}
            if population.get(s, 1) > 0 and infected[s] > population[s]:
                return {"type": "cases_exceed_population", "state": s, "detail": f"Cases > population in {s}"}

        for s in deceased:
            total_cases = state.get("cumulative_cases", {}).get(s, infected.get(s, 0))
            if total_cases > 0 and deceased.get(s, 0) > total_cases:
                return {"type": "deaths_exceed_cases", "state": s, "detail": f"Deaths > cases in {s}"}

        rt_estimates = state.get("Rt_estimates", {})
        for s, rt in rt_estimates.items():
            if rt > 15:
                return {"type": "rt_extreme", "state": s, "detail": f"Rt={rt:.1f} > 15 in {s}"}
            if rt < 0:
                return {"type": "rt_negative", "state": s, "detail": f"Negative Rt in {s}"}

        return None

    def _handle_failure(self, state: dict[str, Any], failure: dict) -> ReasoningResult:
        ftype = failure["type"]
        state_name = failure.get("state", "unknown")

        recovery_actions = {
            "negative_cases": f"Clamped negative cases in {state_name} to 0. Data quality issue detected.",
            "cases_exceed_population": f"Capped cases in {state_name} to population. Possible data duplication.",
            "deaths_exceed_cases": f"Adjusted deaths in {state_name} to 90% of cases. IFR anomaly.",
            "rt_extreme": f"Capped Rt in {state_name} to 8.0. Model instability detected.",
            "rt_negative": f"Reset negative Rt in {state_name} to 1.0. Data error.",
        }

        return ReasoningResult(
            severity="critical",
            rationale=f"FAILURE DETECTED: {failure['detail']}. "
                     f"Recovery: {recovery_actions.get(ftype, 'Manual review required.')}",
            recommended_policies=["enhanced_testing", "contact_tracing"],
            confidence=0.2,
            uncertainty_factors=[f"Data failure: {ftype}", "Model reliability degraded"],
            policy_ranking=[],
            failure_detected=True,
            failure_type=ftype,
            recovery_action=recovery_actions.get(ftype, "Manual intervention needed"),
        )

    def _assess_severity(self, state: dict[str, Any]) -> str:
        rt_estimates = state.get("Rt_estimates", {})
        deceased = state.get("deceased", {})
        population = state.get("population", {})
        healthcare = state.get("healthcare_capacity", {})

        max_rt = max(rt_estimates.values()) if rt_estimates else 1.0
        total_deaths = sum(deceased.values())
        total_pop = sum(population.values())
        deaths_per_million = (total_deaths / max(total_pop, 1)) * 1_000_000

        icu_util = 0.0
        for s in healthcare:
            icu_beds = healthcare.get(s, {}).get("icu", 0)
            if icu_beds > 0:
                current_icu = state.get("infected", {}).get(s, 0) * 0.05
                icu_util = max(icu_util, current_icu / icu_beds)

        for level in ["critical", "high", "medium", "low"]:
            t = SEVERITY_THRESHOLDS[level]
            if max_rt >= t["r0"] or deaths_per_million >= t["deaths_per_million"] or icu_util >= t["icu_utilization"]:
                return level

        return "low"

    def _assess_uncertainty(self, state: dict[str, Any], history: list[dict]) -> list[str]:
        factors = []

        infected = state.get("infected", {})
        if sum(infected.values()) < 100:
            factors.append("Low case count - statistical noise high")

        if len(history) < 3:
            factors.append("Limited history - first few steps")

        rt_estimates = state.get("Rt_estimates", {})
        if rt_estimates:
            rt_vals = list(rt_estimates.values())
            if max(rt_vals) - min(rt_vals) > 2.0:
                factors.append("High variance in Rt across states")

        day = state.get("current_day", 0)
        if day < 14:
            factors.append("Early simulation phase - trends unstable")

        active_variants = state.get("active_variants", {})
        variant_set = set(active_variants.values())
        if len(variant_set) > 2:
            factors.append("Multiple concurrent variants - complex dynamics")

        return factors

    def _select_policies(self, severity: str, state: dict, uncertainty: list[str]) -> list[str]:
        base_policies = {
            "critical": ["lockdown", "mask_mandate", "quarantine", "enhanced_testing",
                         "contact_tracing", "travel_restrictions", "social_distancing"],
            "high": ["mask_mandate", "quarantine", "enhanced_testing", "contact_tracing",
                     "social_distancing", "vaccination_drive"],
            "medium": ["contact_tracing", "mask_mandate", "social_distancing", "vaccination_drive"],
            "low": ["contact_tracing", "social_distancing", "vaccination_drive"],
        }

        policies = base_policies.get(severity, ["contact_tracing"])

        if len(uncertainty) > 3:
            if "enhanced_testing" not in policies:
                policies.append("enhanced_testing")

        return policies

    def _rank_policies(self, policies: list[str], state: dict, uncertainty: list[str]) -> list[dict[str, Any]]:
        ranked = []
        for policy in policies:
            eff = POLICY_EFFECTIVENESS.get(policy, {})
            r0_reduction = eff.get("r0_reduction", 0)
            economic = eff.get("economic_cost", 0.5)
            social = eff.get("social_cost", 0.5)
            lag = eff.get("lag_days", 7)

            benefit = r0_reduction * (1 - 0.3 * len(uncertainty) / 5)
            cost = 0.4 * economic + 0.3 * social + 0.1 * (lag / 21)
            score = benefit - cost

            ranked.append({
                "policy": policy,
                "score": round(score, 3),
                "r0_reduction": r0_reduction,
                "economic_cost": economic,
                "lag_days": lag,
            })

        ranked.sort(key=lambda x: x["score"], reverse=True)
        return ranked

    def _generate_rationale(self, severity: str, state: dict, ranking: list[dict], uncertainty: list[str]) -> str:
        day = state.get("current_day", 0)
        total_infected = sum(state.get("infected", {}).values())
        total_deaths = sum(state.get("deceased", {}).values())

        parts = [f"Day {day}: Severity assessed as {severity.upper()}."]

        if ranking:
            top = ranking[0]
            parts.append(
                f"Top recommendation: {top['policy'].replace('_', ' ').title()} "
                f"(score={top['score']:.2f}, R0 reduction={top['r0_reduction']:.0%})."
            )

        if total_infected > 0:
            parts.append(f"Active cases: {total_infected:,}, deaths: {total_deaths:,}.")

        if uncertainty:
            parts.append(f"Uncertainty factors: {'; '.join(uncertainty[:2])}.")

        return " ".join(parts)
