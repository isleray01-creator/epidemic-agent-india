from __future__ import annotations

import logging
import traceback
from typing import Literal

from langgraph.graph import END, StateGraph

from ..state import EpidemicState
from .nodes import (
    _clean_state,
    analyze_situation,
    detect_shocks,
    evaluate_objective,
    finalize_recommendation,
    implement_or_adapt,
    llm_reasoning,
    multi_agent_debate,
    select_interventions,
    simulate_outcomes,
)

logger = logging.getLogger(__name__)


class EpidemicWorkflow:
    def __init__(self):
        self.graph = self._build_graph()

    def _build_graph(self) -> StateGraph:
        workflow = StateGraph(EpidemicState)

        workflow.add_node("analyze_situation", analyze_situation)
        workflow.add_node("detect_shocks", detect_shocks)
        workflow.add_node("llm_reasoning", llm_reasoning)
        workflow.add_node("multi_agent_debate", multi_agent_debate)
        workflow.add_node("select_interventions", select_interventions)
        workflow.add_node("simulate_outcomes", simulate_outcomes)
        workflow.add_node("evaluate_objective", evaluate_objective)
        workflow.add_node("implement_or_adapt", implement_or_adapt)
        workflow.add_node("finalize_recommendation", finalize_recommendation)

        workflow.set_entry_point("analyze_situation")

        workflow.add_edge("analyze_situation", "detect_shocks")
        workflow.add_edge("detect_shocks", "llm_reasoning")
        workflow.add_edge("llm_reasoning", "multi_agent_debate")
        workflow.add_edge("multi_agent_debate", "select_interventions")
        workflow.add_edge("select_interventions", "simulate_outcomes")
        workflow.add_edge("simulate_outcomes", "evaluate_objective")
        workflow.add_edge("evaluate_objective", "implement_or_adapt")

        workflow.add_conditional_edges(
            "implement_or_adapt",
            self._should_adapt,
            {
                "replan": "llm_reasoning",
                "finalize": "finalize_recommendation",
            },
        )

        workflow.add_edge("finalize_recommendation", END)

        return workflow.compile()

    def _should_adapt(self, state: EpidemicState) -> Literal["replan", "finalize"]:
        needs_replan = state.get("metadata", {}).get("needs_replan", False)
        if needs_replan:
            return "replan"
        return "finalize"

    def run(self, initial_state: EpidemicState) -> EpidemicState:
        try:
            result = self.graph.invoke(initial_state)
            return _clean_state(result)
        except Exception as e:
            logger.error(f"Workflow failed: {e}", exc_info=True)
            error_state = initial_state.copy()
            error_state["metadata"] = error_state.get("metadata", {})
            error_state["metadata"]["error"] = str(e)
            error_state["metadata"]["error_traceback"] = traceback.format_exc()
            error_state["metadata"]["run_complete"] = True
            error_state["metadata"]["final_recommendation"] = {
                "error": True,
                "error_message": f"Workflow execution failed: {e}",
                "recommended_interventions": [],
                "confidence": 0.0,
            }
            return _clean_state(error_state)

    def run_step(self, state: EpidemicState) -> EpidemicState:
        try:
            result = self.graph.invoke(state)
            return _clean_state(result)
        except Exception as e:
            logger.error(f"Workflow step failed: {e}", exc_info=True)
            error_state = state.copy()
            error_state["metadata"] = error_state.get("metadata", {}).copy()
            error_state["metadata"]["error"] = str(e)
            error_state["metadata"]["error_traceback"] = traceback.format_exc()
            return _clean_state(error_state)


_workflow: EpidemicWorkflow | None = None


def get_workflow() -> EpidemicWorkflow:
    global _workflow
    if _workflow is None:
        _workflow = EpidemicWorkflow()
    return _workflow
