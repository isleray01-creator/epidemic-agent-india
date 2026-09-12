"""Epidemic Response Agent for India - Agentic AI epidemic simulation and response planning."""

__version__ = "0.1.0"
__author__ = "Epidemic Agent Team"

from .config import INDIA_STATES, OBJECTIVE_WEIGHTS, settings
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


def get_workflow():
    from .graph import get_workflow as _get_workflow
    return _get_workflow()


class EpidemicWorkflow:
    def __new__(cls, *args, **kwargs):
        from .graph import EpidemicWorkflow as _EW
        return _EW(*args, **kwargs)
