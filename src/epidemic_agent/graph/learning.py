"""Experience replay memory for self-learning from past decisions.

Stores (state, action, outcome) tuples and learns from them.
"""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any

import numpy as np

logger = logging.getLogger(__name__)

MEMORY_DIR = Path(__file__).resolve().parent.parent.parent.parent / "data" / "memory"


@dataclass
class Experience:
    day: int
    state_snapshot: dict[str, Any]
    policies_selected: list[str]
    severity: str
    outcome: dict[str, Any]
    reward: float = 0.0
    rationale: str = ""
    confidence: float = 0.5


@dataclass
class PolicyPerformance:
    policy: str
    times_used: int = 0
    avg_reward: float = 0.0
    avg_r0_reduction: float = 0.0
    avg_deaths_averted: float = 0.0
    success_rate: float = 0.5


class ExperienceMemory:
    """Stores and learns from past simulation experiences."""

    def __init__(self, memory_dir: Path = MEMORY_DIR, max_size: int = 1000):
        self.memory_dir = memory_dir
        self.memory_dir.mkdir(parents=True, exist_ok=True)
        self.max_size = max_size
        self.experiences: list[Experience] = []
        self.policy_performance: dict[str, PolicyPerformance] = {}
        self._load_memory()

    def _memory_path(self) -> Path:
        return self.memory_dir / "experience_replay.json"

    def _load_memory(self):
        path = self._memory_path()
        if path.exists():
            try:
                with open(path, "r") as f:
                    data = json.load(f)
                self.experiences = [Experience(**e) for e in data.get("experiences", [])]
                for p, v in data.get("policy_performance", {}).items():
                    self.policy_performance[p] = PolicyPerformance(**v)
                logger.info(f"Loaded {len(self.experiences)} experiences from memory")
            except Exception as e:
                logger.warning(f"Failed to load memory: {e}")

    def _save_memory(self):
        path = self._memory_path()
        try:
            data = {
                "experiences": [asdict(e) for e in self.experiences[-self.max_size:]],
                "policy_performance": {k: asdict(v) for k, v in self.policy_performance.items()},
            }
            with open(path, "w") as f:
                json.dump(data, f, indent=2, default=str)
        except Exception as e:
            logger.warning(f"Failed to save memory: {e}")

    def record_experience(
        self,
        day: int,
        state: dict[str, Any],
        policies: list[str],
        severity: str,
        outcome: dict[str, Any],
        rationale: str = "",
        confidence: float = 0.5,
    ):
        reward = self._compute_reward(state, outcome)

        exp = Experience(
            day=day,
            state_snapshot=self._compress_state(state),
            policies_selected=policies,
            severity=severity,
            outcome=outcome,
            reward=reward,
            rationale=rationale,
            confidence=confidence,
        )

        self.experiences.append(exp)
        if len(self.experiences) > self.max_size:
            self.experiences = self.experiences[-self.max_size:]

        for policy in policies:
            if policy not in self.policy_performance:
                self.policy_performance[policy] = PolicyPerformance(policy=policy)

            pp = self.policy_performance[policy]
            pp.times_used += 1
            n = pp.times_used
            pp.avg_reward = pp.avg_reward * (n - 1) / n + reward / n
            pp.avg_r0_reduction = pp.avg_r0_reduction * (n - 1) / n + outcome.get("r0_reduction", 0) / n
            pp.avg_deaths_averted = pp.avg_deaths_averted * (n - 1) / n + outcome.get("deaths_averted", 0) / n
            pp.success_rate = pp.success_rate * (n - 1) / n + (1.0 if reward > 0 else 0.0) / n

        self._save_memory()

    def _compute_reward(self, state: dict, outcome: dict) -> float:
        deaths = outcome.get("deaths", 0)
        r0 = outcome.get("r0_after", 1.0)
        economic = outcome.get("economic_cost", 0)

        death_penalty = -min(deaths / 1000, 1.0)
        r0_bonus = max(0, (2.0 - r0) / 2.0) * 0.5
        cost_penalty = -min(economic / 1e9, 0.5)

        return death_penalty + r0_bonus + cost_penalty

    def _compress_state(self, state: dict) -> dict[str, Any]:
        return {
            "current_day": state.get("current_day", 0),
            "total_infected": sum(state.get("infected", {}).values()),
            "total_deceased": sum(state.get("deceased", {}).values()),
            "rt_estimates": state.get("Rt_estimates", {}),
            "active_variants": state.get("active_variants", {}),
        }

    def get_policy_advice(self, severity: str) -> dict[str, Any]:
        if not self.policy_performance:
            return {"advice": "No history available", "best_policies": [], "confidence": 0.0}

        scored = []
        for policy, pp in self.policy_performance.items():
            if pp.times_used < 2:
                continue
            score = pp.avg_reward * 0.4 + pp.success_rate * 0.3 + pp.avg_r0_reduction * 0.3
            scored.append({"policy": policy, "score": round(score, 3), "success_rate": round(pp.success_rate, 3)})

        scored.sort(key=lambda x: x["score"], reverse=True)

        severity_preferences = {
            "critical": ["lockdown", "quarantine", "mask_mandate"],
            "high": ["mask_mandate", "quarantine", "enhanced_testing"],
            "medium": ["contact_tracing", "social_distancing", "vaccination_drive"],
            "low": ["contact_tracing", "social_distancing"],
        }
        preferred = severity_preferences.get(severity, [])

        for p in scored:
            if p["policy"] in preferred:
                p["score"] *= 1.2

        scored.sort(key=lambda x: x["score"], reverse=True)

        return {
            "advice": f"Based on {len(self.experiences)} past experiences",
            "best_policies": [s["policy"] for s in scored[:3]],
            "policy_scores": scored[:5],
            "confidence": min(0.9, len(self.experiences) / 100),
        }

    def get_recent_trend(self, window: int = 5) -> dict[str, Any]:
        recent = self.experiences[-window:]
        if not recent:
            return {"trend": "unknown", "avg_reward": 0.0}

        rewards = [e.reward for e in recent]
        avg = np.mean(rewards)
        trend = "improving" if len(rewards) > 1 and rewards[-1] > rewards[0] else "stable"

        return {
            "trend": trend,
            "avg_reward": float(avg),
            "recent_rewards": rewards,
            "window": window,
        }

    def get_memory_stats(self) -> dict[str, Any]:
        return {
            "total_experiences": len(self.experiences),
            "policies_learned": len(self.policy_performance),
            "avg_reward": float(np.mean([e.reward for e in self.experiences])) if self.experiences else 0,
            "best_policy": max(
                self.policy_performance.items(),
                key=lambda x: x[1].avg_reward,
            )[0] if self.policy_performance else "none",
        }
