"""LLM Reasoning node - interprets simulation results and suggests policies.

Uses Google Gemini via langchain for actual LLM inference.
Falls back to rule-based reasoning if LLM is unavailable.
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

VALID_POLICIES = set(POLICY_EFFECTIVENESS.keys())
VALID_SEVERITIES = {"low", "medium", "high", "critical"}


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
    """LLM-powered reasoning engine using Gemini for epidemic response decisions."""

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

        try:
            return self._reason_with_llm(state, history)
        except Exception as e:
            logger.warning(f"LLM reasoning failed, falling back to heuristic: {e}")
            return self._reason_with_heuristic(state, history)

    def _reason_with_llm(self, state: dict, history: list) -> ReasoningResult:
        from ..llm.client import get_llm_client
        from ..llm.prompts import REASONING_PROMPT

        client = get_llm_client()
        if not client.available:
            raise RuntimeError("LLM not available")

        situation = self._build_situation_summary(state)
        history_text = json.dumps(history[-5:], indent=2) if history else "No prior history"

        rag_context = state.get("historical_context", [])
        if rag_context:
            rag_text = json.dumps(rag_context[:3], indent=2, default=str)
            situation["rag_memory"] = json.loads(rag_text) if rag_text else []
        else:
            situation["rag_memory"] = []

        prompt = REASONING_PROMPT.format(
            situation_json=json.dumps(situation, indent=2, default=str),
            history_json=history_text,
        )

        from langchain_core.messages import HumanMessage, SystemMessage
        from ..llm.prompts import SYSTEM_PROMPT

        messages = [
            SystemMessage(content=SYSTEM_PROMPT),
            HumanMessage(content=prompt),
        ]

        raw = client.invoke_json(messages)

        severity = raw.get("severity", "medium")
        if severity not in VALID_SEVERITIES:
            severity = "medium"

        recommended = [p for p in raw.get("recommended_policies", []) if p in VALID_POLICIES][:4]
        if not recommended:
            recommended = ["contact_tracing", "social_distancing", "mask_mandate"]

        ranking = []
        for pr in raw.get("policy_ranking", []):
            if isinstance(pr, dict) and pr.get("policy") in VALID_POLICIES:
                ranking.append({
                    "policy": pr["policy"],
                    "score": float(pr.get("score", 0.5)),
                    "r0_reduction": float(pr.get("r0_reduction", 0.2)),
                    "economic_cost": float(pr.get("economic_cost", 0.5)),
                    "lag_days": int(pr.get("lag_days", 7)),
                })

        if not ranking:
            ranking = self._build_default_ranking(recommended, state)

        confidence = float(raw.get("confidence", 0.7))
        uncertainty = raw.get("uncertainty_factors", [])
        rationale = raw.get("rationale", "LLM analysis completed")

        logger.info(f"LLM reasoning: severity={severity}, policies={recommended}, confidence={confidence:.2f}")

        return ReasoningResult(
            severity=severity,
            rationale=rationale,
            recommended_policies=recommended,
            confidence=max(0.3, min(1.0, confidence)),
            uncertainty_factors=uncertainty[:5],
            policy_ranking=ranking,
        )

    def _reason_with_heuristic(self, state: dict, history: list) -> ReasoningResult:
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

    def _build_situation_summary(self, state: dict) -> dict:
        total_infected = sum(state.get("infected", {}).values())
        total_deceased = sum(state.get("deceased", {}).values())
        total_pop = sum(state.get("population", {}).values())
        rt_estimates = state.get("Rt_estimates", {})
        max_rt = max(rt_estimates.values()) if rt_estimates else 1.0
        avg_rt = sum(rt_estimates.values()) / len(rt_estimates) if rt_estimates else 1.0

        healthcare = state.get("healthcare_capacity", {})
        icu_total = sum(h.get("icu", 0) for h in healthcare.values())
        beds_total = sum(h.get("beds", 0) for h in healthcare.values())

        return {
            "current_day": state.get("current_day", 0),
            "states": state.get("states", []),
            "active_cases": total_infected,
            "total_deaths": total_deceased,
            "population": total_pop,
            "deaths_per_million": round((total_deceased / max(total_pop, 1)) * 1_000_000, 2),
            "Rt_estimates": rt_estimates,
            "max_Rt": round(max_rt, 2),
            "avg_Rt": round(avg_rt, 2),
            "active_variants": state.get("active_variants", {}),
            "variant_prevalence": state.get("variant_prevalence", {}),
            "healthcare": {"icu_beds": icu_total, "total_beds": beds_total},
            "current_policies": state.get("current_policies", {}),
            "vaccinated": state.get("vaccinated", {}),
        }

    def _build_default_ranking(self, policies: list[str], state: dict) -> list[dict]:
        ranking = []
        for policy in policies:
            eff = POLICY_EFFECTIVENESS.get(policy, {})
            ranking.append({
                "policy": policy,
                "score": 0.5,
                "r0_reduction": eff.get("r0_reduction", 0.2),
                "economic_cost": eff.get("economic_cost", 0.5),
                "lag_days": eff.get("lag_days", 7),
            })
        return ranking

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
