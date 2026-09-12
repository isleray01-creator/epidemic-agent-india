"""Multi-agent debate system - epidemiologist, economist, public health specialist.

Each agent evaluates policies from their domain perspective.
A consensus mechanism resolves disagreements.
"""
from __future__ import annotations

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


class Agent:
    def __init__(self, name: str, expertise: str, weights: dict[str, float]):
        self.name = name
        self.expertise = expertise
        self.weights = weights

    def evaluate(self, policies: list[str], state: dict, severity: str) -> list[AgentVote]:
        raise NotImplementedError


class EpidemiologistAgent(Agent):
    def __init__(self):
        super().__init__(
            name="Epidemiologist",
            expertise="disease_transmission",
            weights={"r0_reduction": 0.5, "deaths_averted": 0.3, "speed": 0.2},
        )

    def evaluate(self, policies: list[str], state: dict, severity: str) -> list[AgentVote]:
        votes = []
        rt = max(state.get("Rt_estimates", {}).values()) if state.get("Rt_estimates") else 1.0
        infected = sum(state.get("infected", {}).values())

        for policy in policies:
            support = 0.5
            rationale_parts = []

            if policy in ["lockdown", "quarantine", "mask_mandate"]:
                support += 0.2
                rationale_parts.append(f"Directly reduces transmission (Rt={rt:.1f})")

            if policy == "vaccination_drive" and severity in ["high", "critical"]:
                support += 0.15
                rationale_parts.append("Long-term immunity build-up needed")

            if policy == "contact_tracing":
                if infected < 10000:
                    support += 0.1
                    rationale_parts.append("Effective at lower case counts")
                else:
                    support -= 0.1
                    rationale_parts.append("Less effective at high case counts")

            if policy == "enhanced_testing" and severity in ["medium", "high"]:
                support += 0.1
                rationale_parts.append("Identifies hidden transmission chains")

            if severity == "critical" and policy not in ["lockdown", "quarantine"]:
                support -= 0.15
                rationale_parts.append("Critical severity demands strongest measures")

            support = max(0.1, min(0.95, support))
            votes.append(AgentVote(
                agent=self.name, policy=policy, support=support,
                rationale="; ".join(rationale_parts) or "Standard epidemiological assessment",
                confidence=0.8 if severity in ["critical", "high"] else 0.6,
            ))

        return votes


class EconomistAgent(Agent):
    def __init__(self):
        super().__init__(
            name="Economist",
            expertise="economic_impact",
            weights={"cost_benefit": 0.4, "economic_recovery": 0.3, "gdp_impact": 0.3},
        )

    def evaluate(self, policies: list[str], state: dict, severity: str) -> list[AgentVote]:
        votes = []
        population = sum(state.get("population", {}).values())

        for policy in policies:
            support = 0.5
            rationale_parts = []

            cost_map = {
                "lockdown": 0.9, "travel_restrictions": 0.6,
                "quarantine": 0.4, "mask_mandate": 0.15,
                "vaccination_drive": 0.35, "enhanced_testing": 0.25,
                "contact_tracing": 0.2, "social_distancing": 0.3,
            }

            cost = cost_map.get(policy, 0.5)

            if cost > 0.6:
                support -= 0.2
                rationale_parts.append(f"High economic cost ({cost:.0%} impact)")
            elif cost < 0.2:
                support += 0.15
                rationale_parts.append(f"Low economic cost ({cost:.0%} impact)")
            else:
                support += 0.05
                rationale_parts.append(f"Moderate economic cost ({cost:.0%} impact)")

            if severity == "low" and cost > 0.5:
                support -= 0.25
                rationale_parts.append("Low severity does not justify high economic cost")

            if policy == "vaccination_drive":
                support += 0.1
                rationale_parts.append("Long-term economic recovery enabler")

            support = max(0.1, min(0.95, support))
            votes.append(AgentVote(
                agent=self.name, policy=policy, support=support,
                rationale="; ".join(rationale_parts) or "Standard economic assessment",
                confidence=0.7,
            ))

        return votes


class PublicHealthAgent(Agent):
    def __init__(self):
        super().__init__(
            name="PublicHealth",
            expertise="social_impact",
            weights={"compliance": 0.3, "equity": 0.3, "mental_health": 0.2, "education": 0.2},
        )

    def evaluate(self, policies: list[str], state: dict, severity: str) -> list[AgentVote]:
        votes = []

        for policy in policies:
            support = 0.5
            rationale_parts = []

            social_costs = {
                "lockdown": 0.85, "quarantine": 0.6, "travel_restrictions": 0.5,
                "mask_mandate": 0.2, "social_distancing": 0.35,
                "vaccination_drive": 0.1, "enhanced_testing": 0.15, "contact_tracing": 0.2,
            }

            social_cost = social_costs.get(policy, 0.5)

            if social_cost > 0.6:
                support -= 0.15
                rationale_parts.append(f"High social burden ({social_cost:.0%})")
            elif social_cost < 0.2:
                support += 0.15
                rationale_parts.append(f"Low social burden ({social_cost:.0%})")

            compliance_rates = {
                "mask_mandate": 0.65, "social_distancing": 0.55,
                "quarantine": 0.60, "lockdown": 0.50,
                "vaccination_drive": 0.70, "contact_tracing": 0.45,
                "enhanced_testing": 0.55, "travel_restrictions": 0.40,
            }

            compliance = compliance_rates.get(policy, 0.5)
            if compliance < 0.5:
                support -= 0.1
                rationale_parts.append(f"Low compliance expected ({compliance:.0%})")
            elif compliance > 0.65:
                support += 0.1
                rationale_parts.append(f"Good compliance expected ({compliance:.0%})")

            if severity == "critical":
                if policy in ["lockdown", "quarantine"]:
                    support += 0.1
                    rationale_parts.append("Critical situation justifies social cost")

            support = max(0.1, min(0.95, support))
            votes.append(AgentVote(
                agent=self.name, policy=policy, support=support,
                rationale="; ".join(rationale_parts) or "Standard public health assessment",
                confidence=0.65,
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
