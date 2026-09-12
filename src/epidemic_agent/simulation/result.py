from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass
class SimulationResult:
    daily_cases: dict[str, list[int]]
    daily_deaths: dict[str, list[int]]
    daily_Rt: dict[str, list[float]]
    cumulative_cases: dict[str, list[int]]
    cumulative_deaths: dict[str, list[int]]
    peak_day: dict[str, int]
    peak_cases: dict[str, int]
    total_deaths: dict[str, int]
    final_infected: dict[str, int]
    variant_trajectory: dict[str, list[str]]
    metadata: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
