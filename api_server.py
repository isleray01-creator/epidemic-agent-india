"""EpiPulse FastAPI Bridge Server
Connects the React frontend to the Python epidemic-agent-india backend.
Run: python -m api_server
Port: 8000
"""
import sys
import os
from pathlib import Path
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional

# Add project root to path
project_root = Path(__file__).parent
src_dir = project_root / "src"
if str(src_dir) not in sys.path:
    sys.path.insert(0, str(src_dir))

app = FastAPI(title="EpiPulse API", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173", "http://127.0.0.1:3000", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class SimulateRequest(BaseModel):
    model_type: str = "seir"
    states: list[str] = Field(default_factory=lambda: ["Maharashtra", "Kerala", "Delhi"])
    variant: str = "wildtype"
    days: int = 60
    interventions: list[str] = Field(default_factory=lambda: ["contact_tracing"])
    initial_infected: int = 100
    population: int = 0


class WorkflowRequest(BaseModel):
    states: list[str] = Field(default_factory=lambda: ["Maharashtra", "Kerala", "Delhi"])
    days: int = 60
    initial_infected: int = 100
    variant: str = "wildtype"
    interventions: list[str] = Field(default_factory=lambda: ["contact_tracing"])


@app.get("/api/health")
def health_check():
    return {"status": "ok", "version": "2.0.0", "backend": "epidemic-agent-india"}


@app.get("/api/config/variants")
def get_variants():
    try:
        from epidemic_agent.config import VARIANT_PARAMS
        return {"variants": VARIANT_PARAMS}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/config/states")
def get_states():
    try:
        from epidemic_agent.config import INDIA_STATES, get_state_population
        states_info = []
        for state in INDIA_STATES:
            pop = get_state_population(state)
            states_info.append({"name": state, "population": pop})
        return {"states": states_info}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/simulate")
def simulate(req: SimulateRequest):
    try:
        from epidemic_agent.tools.simulator import simulate_spread
        # simulate_spread is decorated with @register_tool, making it a StructuredTool instance
        func = getattr(simulate_spread, "func", simulate_spread)
        result = func(
            model_type=req.model_type,
            states=req.states,
            variant=req.variant,
            days=req.days,
            interventions=req.interventions,
            initial_infected=req.initial_infected,
            population=req.population if req.population > 0 else None,
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/simulate/seir")
def simulate_seir(req: SimulateRequest):
    try:
        from epidemic_agent.simulation.seir_model import run_seir_simulation
        from epidemic_agent.config import get_state_population

        states = req.states
        populations = {s: get_state_population(s) for s in states}
        total_pop = sum(populations.values()) if req.population == 0 else req.population

        result = run_seir_simulation(
            population=total_pop,
            R0=2.5,
            IFR=0.01,
            immune_escape=0.0,
            serial_interval=5.0,
            incubation_period=5.2,
            infectious_period=7.0,
            days=req.days,
            states=states,
            initial_infected=req.initial_infected,
        )
        return result.to_dict()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/workflow/run")
def run_workflow(req: WorkflowRequest):
    try:
        from epidemic_agent.graph.workflow import get_workflow
        from epidemic_agent.state import EpidemicState
        from epidemic_agent.config import get_state_population, settings

        populations = {s: get_state_population(s) for s in req.states}

        initial_state: EpidemicState = {
            "current_day": 0,
            "simulation_days": req.days,
            "country": "India",
            "states": req.states,
            "population": populations,
            "infected": {s: req.initial_infected for s in req.states},
            "exposed": {s: req.initial_infected * 2 for s in req.states},
            "recovered": {s: 0 for s in req.states},
            "deceased": {s: 0 for s in req.states},
            "vaccinated": {s: 0 for s in req.states},
            "active_variants": {s: req.variant for s in req.states},
            "variant_prevalence": {s: {req.variant: 1.0} for s in req.states},
            "current_policies": {s: req.interventions for s in req.states},
            "intervention_history": [],
            "variant_shock": None,
            "confidence_score": 0.8,
            "objective_value": 0.0,
            "objective_breakdown": {},
            "Rt_estimates": {s: 2.5 for s in req.states},
            "healthcare_capacity": {s: {"beds": 1000, "icu": 100, "ventilators": 50} for s in req.states},
            "contact_tracing_metrics": {s: {"coverage": 0.0, "delay": 0} for s in req.states},
            "metadata": {},
        }

        workflow = get_workflow()
        final_state = workflow.run(initial_state)
        return {"success": True, "result": dict(final_state)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
