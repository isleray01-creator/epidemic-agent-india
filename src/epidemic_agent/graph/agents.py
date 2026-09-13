"""Multi-agent debate system - epidemiologist, economist, public health specialist.

Uses Google Gemini to generate agent rationales and evaluations.
Falls back to heuristic scoring if LLM is unavailable.
"""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class AgentVote:
    agent: str
    policy: str
    support: float
    rationale: str
    confidence: float


@dataclass
class DebateResult:
    consensus_policies: list[str]
    votes: list[AgentVote]
    agreement_score: float
    dissenting_opinions: list[str]
    reasoning: str


AGENT_CONFIGS = {
    "Epidemiologist": {
        "expertise": "disease transmission dynamics, R0 estimation, variant evolution, contact tracing effectiveness",
        "weights": {"r0_reduction": 0.5, "deaths_averted": 0.3, "speed": 0.2},
        "support_adjustments": {
            "lockdown": 0.2, "quarantine": 0.2, "mask_mandate": 0.2,
            "vaccination_drive": 0.15, "contact_tracing": 0.1,
            "enhanced_testing": 0.1, "travel_restrictions": 0.15,
        },
    },
    "Economist": {
        "expertise": "health economics, GDP impact, informal sector analysis, cost-effectiveness of interventions",
        "weights": {"cost_benefit": 0.4, "economic_recovery": 0.3, "gdp_impact": 0.3},
        "support_adjustments": {
            "lockdown": -0.3, "quarantine": -0.15, "mask_mandate": 0.1,
            "vaccination_drive": 0.15, "contact_tracing": 0.1,
            "enhanced_testing": 0.05, "travel_restrictions": -0.2,
            "social_distancing": 0.05,
        },
    },
    "PublicHealth": {
        "expertise": "social impact, compliance behavior, mental health, education disruption, equity",
        "weights": {"compliance": 0.3, "equity": 0.3, "mental_health": 0.2, "education": 0.2},
        "support_adjustments": {
            "lockdown": -0.2, "quarantine": -0.1, "mask_mandate": 0.15,
            "vaccination_drive": 0.2, "contact_tracing": 0.1,
            "enhanced_testing": 0.1, "travel_restrictions": -0.1,
            "social_distancing": 0.1,
        },
    },
}


class Agent:
    def __init__(self, name: str, expertise: str, weights: dict[str, float]):
        self.name = name
        self.expertise = expertise
        self.weights = weights

    def evaluate(self, policies: list[str], state: dict, severity: str) -> list[AgentVote]:
        raise NotImplementedError


class EpidemiologistAgent(Agent):
    def __init__(self):
        cfg = AGENT_CONFIGS["Epidemiologist"]
        super().__init__("Epidemiologist", cfg["expertise"], cfg["weights"])

    def evaluate(self, policies: list[str], state: dict, severity: str) -> list[AgentVote]:
        return _evaluate_with_llm_or_heuristic(self.name, policies, state, severity)


class EconomistAgent(Agent):
    def __init__(self):
        cfg = AGENT_CONFIGS["Economist"]
        super().__init__("Economist", cfg["expertise"], cfg["weights"])

    def evaluate(self, policies: list[str], state: dict, severity: str) -> list[AgentVote]:
        return _evaluate_with_llm_or_heuristic(self.name, policies, state, severity)


class PublicHealthAgent(Agent):
    def __init__(self):
        cfg = AGENT_CONFIGS["PublicHealth"]
        super().__init__("PublicHealth", cfg["expertise"], cfg["weights"])

    def evaluate(self, policies: list[str], state: dict, severity: str) -> list[AgentVote]:
        return _evaluate_with_llm_or_heuristic(self.name, policies, state, severity)


def _evaluate_with_llm_or_heuristic(agent_name: str, policies: list[str], state: dict, severity: str) -> list[AgentVote]:
    try:
        return _evaluate_with_llm(agent_name, policies, state, severity)
    except Exception as e:
        logger.warning(f"LLM evaluation failed for {agent_name}, using heuristic: {e}")
        return _evaluate_with_heuristic(agent_name, policies, state, severity)


def _evaluate_with_llm(agent_name: str, policies: list[str], state: dict, severity: str) -> list[AgentVote]:
    from ..llm.client import get_llm_client
    from ..llm.prompts import AGENT_EVAL_PROMPT, SYSTEM_PROMPT

    client = get_llm_client()
    if not client.available:
        raise RuntimeError("LLM not available")

    cfg = AGENT_CONFIGS[agent_name]

    situation = {
        "current_day": state.get("current_day", 0),
        "active_cases": sum(state.get("infected", {}).values()),
        "total_deaths": sum(state.get("deceased", {}).values()),
        "population": sum(state.get("population", {}).values()),
        "Rt_estimates": state.get("Rt_estimates", {}),
        "active_variants": state.get("active_variants", {}),
        "healthcare_capacity": state.get("healthcare_capacity", {}),
    }

    prompt = AGENT_EVAL_PROMPT.format(
        agent_role=agent_name,
        agent_expertise=cfg["expertise"],
        severity=severity,
        situation_json=json.dumps(situation, indent=2, default=str),
        policies_json=json.dumps(policies, indent=2),
    )

    from langchain_core.messages import HumanMessage, SystemMessage

    messages = [
        SystemMessage(content=SYSTEM_PROMPT),
        HumanMessage(content=prompt),
    ]

    raw = client.invoke_json(messages)
    votes_raw = raw.get("votes", [])

    votes = []
    policy_set = set(policies)
    for v in votes_raw:
        if isinstance(v, dict) and v.get("policy") in policy_set:
            support = max(0.1, min(0.95, float(v.get("support", 0.5))))
            votes.append(AgentVote(
                agent=agent_name,
                policy=v["policy"],
                support=support,
                rationale=v.get("rationale", f"{agent_name} assessment"),
                confidence=0.7,
            ))

    if len(votes) < len(policies):
        evaluated = {v.policy for v in votes}
        for p in policies:
            if p not in evaluated:
                adj = cfg["support_adjustments"].get(p, 0)
                votes.append(AgentVote(
                    agent=agent_name, policy=p,
                    support=max(0.1, min(0.95, 0.5 + adj)),
                    rationale=f"{agent_name} standard assessment",
                    confidence=0.5,
                ))

    logger.info(f"LLM {agent_name} evaluated {len(votes)} policies")
    return votes


def _evaluate_with_heuristic(agent_name: str, policies: list[str], state: dict, severity: str) -> list[AgentVote]:
    votes = []
    cfg = AGENT_CONFIGS[agent_name]
    rt = max(state.get("Rt_estimates", {}).values()) if state.get("Rt_estimates") else 1.0
    infected = sum(state.get("infected", {}).values())

    for policy in policies:
        support = 0.5
        rationale_parts = []

        adj = cfg["support_adjustments"].get(policy, 0)
        support += adj

        if agent_name == "Epidemiologist":
            if rt > 3.0 and policy in ["lockdown", "quarantine"]:
                support += 0.1
                rationale_parts.append(f"High Rt={rt:.1f} justifies strong measures")
            if infected > 50000 and policy == "contact_tracing":
                support -= 0.1
                rationale_parts.append("Contact tracing less effective at high case counts")
        elif agent_name == "Economist":
            cost_map = {
                "lockdown": 0.9, "travel_restrictions": 0.6, "quarantine": 0.4,
                "mask_mandate": 0.15, "vaccination_drive": 0.35, "enhanced_testing": 0.25,
                "contact_tracing": 0.2, "social_distancing": 0.3,
            }
            cost = cost_map.get(policy, 0.5)
            if cost > 0.6 and severity == "low":
                support -= 0.2
                rationale_parts.append(f"High cost ({cost:.0%}) not justified at low severity")
        elif agent_name == "PublicHealth":
            compliance_rates = {
                "mask_mandate": 0.65, "social_distancing": 0.55, "quarantine": 0.60,
                "lockdown": 0.50, "vaccination_drive": 0.70, "contact_tracing": 0.45,
                "enhanced_testing": 0.55, "travel_restrictions": 0.40,
            }
            compliance = compliance_rates.get(policy, 0.5)
            if compliance < 0.5:
                support -= 0.1
                rationale_parts.append(f"Low compliance ({compliance:.0%}) expected")

        support = max(0.1, min(0.95, support))
        votes.append(AgentVote(
            agent=agent_name, policy=policy, support=support,
            rationale="; ".join(rationale_parts) or f"Standard {agent_name.lower()} assessment",
            confidence=0.6,
        ))

    return votes


class MultiAgentDebater:
    """Orchestrates debate between specialist agents."""

    def __init__(self):
        self.agents = [
            EpidemiologistAgent(),
            EconomistAgent(),
            PublicHealthAgent(),
        ]

    def debate(
        self,
        policies: list[str],
        state: dict,
        severity: str,
        rounds: int = 2,
    ) -> DebateResult:
        all_votes: list[AgentVote] = []

        for round_num in range(rounds):
            for agent in self.agents:
                votes = agent.evaluate(policies, state, severity)
                all_votes.extend(votes)

        try:
            return self._debate_with_llm_synthesis(policies, state, severity, all_votes)
        except Exception as e:
            logger.warning(f"LLM debate synthesis failed, using heuristic: {e}")
            return self._debate_with_heuristic(all_votes)

    def _debate_with_llm_synthesis(
        self, policies: list[str], state: dict, severity: str, all_votes: list[AgentVote]
    ) -> DebateResult:
        from ..llm.client import get_llm_client
        from ..llm.prompts import DEBATE_SYNTHESIS_PROMPT, SYSTEM_PROMPT

        client = get_llm_client()
        if not client.available:
            raise RuntimeError("LLM not available")

        votes_data = []
        for v in all_votes:
            votes_data.append({
                "agent": v.agent,
                "policy": v.policy,
                "support": round(v.support, 2),
                "rationale": v.rationale,
            })

        situation = {
            "severity": severity,
            "active_cases": sum(state.get("infected", {}).values()),
            "Rt_estimates": state.get("Rt_estimates", {}),
            "active_variants": state.get("active_variants", {}),
        }

        prompt = DEBATE_SYNTHESIS_PROMPT.format(
            votes_json=json.dumps(votes_data, indent=2),
            situation_json=json.dumps(situation, indent=2, default=str),
        )

        from langchain_core.messages import HumanMessage, SystemMessage

        messages = [
            SystemMessage(content=SYSTEM_PROMPT),
            HumanMessage(content=prompt),
        ]

        raw = client.invoke_json(messages)

        consensus = [p for p in raw.get("consensus_policies", []) if p in set(policies)][:4]
        if not consensus:
            consensus = policies[:3]

        agreement = float(raw.get("agreement_score", 0.6))
        dissenting = raw.get("dissenting_opinions", [])
        synthesis = raw.get("synthesis", "Debate synthesis completed by LLM")

        logger.info(f"LLM debate synthesis: consensus={consensus}, agreement={agreement:.2f}")

        return DebateResult(
            consensus_policies=consensus,
            votes=all_votes,
            agreement_score=max(0.2, min(1.0, agreement)),
            dissenting_opinions=dissenting[:5],
            reasoning=synthesis,
        )

    def _debate_with_heuristic(self, all_votes: list[AgentVote]) -> DebateResult:
        policy_scores: dict[str, list[float]] = {}
        policy_votes: dict[str, list[AgentVote]] = {}
        for vote in all_votes:
            policy_scores.setdefault(vote.policy, []).append(vote.support)
            policy_votes.setdefault(vote.policy, []).append(vote)

        scored_policies = []
        for policy, scores in policy_scores.items():
            avg_score = sum(scores) / len(scores)
            agreement = 1.0 - (max(scores) - min(scores))
            weighted_score = avg_score * 0.7 + agreement * 0.3
            scored_policies.append((policy, weighted_score))

        scored_policies.sort(key=lambda x: x[1], reverse=True)
        consensus = [p for p, s in scored_policies if s >= 0.45][:4]

        all_supports = [v.support for v in all_votes]
        agreement_score = 1.0 - (max(all_supports) - min(all_supports)) if all_supports else 0.5

        dissenting = []
        for policy, votes in policy_votes.items():
            supports = [v.support for v in votes]
            if max(supports) - min(supports) > 0.3:
                low_agent = min(votes, key=lambda v: v.support)
                dissenting.append(f"{low_agent.agent} opposes {policy}: {low_agent.rationale}")

        reasoning_parts = []
        for policy in consensus[:2]:
            policy_vote_details = policy_votes.get(policy, [])
            agent_supports = [f"{v.agent}={v.support:.2f}" for v in policy_vote_details]
            reasoning_parts.append(f"{policy}: [{', '.join(agent_supports)}]")

        return DebateResult(
            consensus_policies=consensus,
            votes=all_votes,
            agreement_score=round(agreement_score, 3),
            dissenting_opinions=dissenting,
            reasoning="Consensus: " + "; ".join(reasoning_parts) if reasoning_parts else "No consensus reached",
        )
