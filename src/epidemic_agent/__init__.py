"""Epidemic Response Agent for India - Agentic AI epidemic simulation and response planning."""

__version__ = "0.1.0"
__author__ = "Epidemic Agent Team"

from .config import INDIA_STATES, OBJECTIVE_WEIGHTS, settings
from .graph import EpidemicWorkflow, get_workflow
from .state import EpidemicState, SimulationConfig

__all__ = [
    "settings",
    "INDIA_STATES",
    "OBJECTIVE_WEIGHTS",
    "EpidemicState",
    "SimulationConfig",
    "get_workflow",
    "EpidemicWorkflow",
]
