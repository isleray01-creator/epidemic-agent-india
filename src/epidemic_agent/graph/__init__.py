def analyze_situation(state):
    from .nodes import analyze_situation as _fn
    return _fn(state)

def detect_shocks(state):
    from .nodes import detect_shocks as _fn
    return _fn(state)

def llm_reasoning(state):
    from .nodes import llm_reasoning as _fn
    return _fn(state)

def multi_agent_debate(state):
    from .nodes import multi_agent_debate as _fn
    return _fn(state)

def select_interventions(state):
    from .nodes import select_interventions as _fn
    return _fn(state)

def simulate_outcomes(state):
    from .nodes import simulate_outcomes as _fn
    return _fn(state)

def evaluate_objective(state):
    from .nodes import evaluate_objective as _fn
    return _fn(state)

def implement_or_adapt(state):
    from .nodes import implement_or_adapt as _fn
    return _fn(state)

def finalize_recommendation(state):
    from .nodes import finalize_recommendation as _fn
    return _fn(state)


def get_workflow():
    from .workflow import get_workflow as _get_workflow
    return _get_workflow()


class EpidemicWorkflow:
    def __new__(cls, *args, **kwargs):
        from .workflow import EpidemicWorkflow as _EW
        return _EW(*args, **kwargs)
