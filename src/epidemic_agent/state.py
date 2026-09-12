from __future__ import annotations

from typing import Any, Literal, TypedDict

from pydantic import BaseModel, Field


class VariantShockInfo(BaseModel):
    shock_detected: bool = False
    anomalies: dict[str, dict[str, Any]] = Field(default_factory=dict)
    recommended_action: str = ""
    severity: Literal["none", "medium", "high"] = "none"


class InterventionRecord(BaseModel):
    day: int
    intervention_type: str
    params: dict[str, Any] = Field(default_factory=dict)
    cost: float
    projected_effect: dict[str, float]


class EpidemicState(TypedDict):
    current_day: int
    simulation_days: int
    country: str
    states: list[str]
    population: dict[str, int]
    infected: dict[str, int]
    exposed: dict[str, int]
    recovered: dict[str, int]
    deceased: dict[str, int]
    vaccinated: dict[str, int]
    active_variants: dict[str, str]
    variant_prevalence: dict[str, dict[str, float]]
    current_policies: dict[str, list[str]]
    intervention_history: list[InterventionRecord]
    variant_shock: VariantShockInfo | None
    confidence_score: float
    objective_value: float
    objective_breakdown: dict[str, float]
    Rt_estimates: dict[str, float]
    healthcare_capacity: dict[str, dict[str, int]]
    contact_tracing_metrics: dict[str, dict[str, float]]
    metadata: dict[str, Any]


class SimulationConfig(BaseModel):
    country: str = "India"
    states: list[str] = Field(default_factory=lambda: ["Maharashtra", "Kerala", "Delhi"])
    population: int = 1_000_000
    days: int = 60
    initial_infected: int = 100
    initial_variant: str = "wildtype"
    interventions: list[str] = Field(default_factory=lambda: ["contact_tracing"])
    contact_tracing_efficiency: float = 0.6
    contact_tracing_compliance: float = 0.7
    random_seed: int = 42


class DashboardState(BaseModel):
    current_frame: int = 0
    total_frames: int = 0
    playing: bool = False
    speed: float = 1.0
    selected_state: str = "All"
    selected_metric: str = "cases"
    show_interventions: bool = True
