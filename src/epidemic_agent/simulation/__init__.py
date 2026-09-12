def run_mesa_simulation(*args, **kwargs):
    from .mesa_model import run_mesa_simulation as _fn
    return _fn(*args, **kwargs)

def run_seir_simulation(*args, **kwargs):
    from .seir_model import run_seir_simulation as _fn
    return _fn(*args, **kwargs)

class EpidemicModel:
    def __new__(cls, *args, **kwargs):
        from .mesa_model import EpidemicModel as _EM
        return _EM(*args, **kwargs)

class PersonAgent:
    def __new__(cls, *args, **kwargs):
        from .mesa_model import PersonAgent as _PA
        return _PA(*args, **kwargs)

class SEIRModel:
    def __new__(cls, *args, **kwargs):
        from .seir_model import SEIRModel as _SM
        return _SM(*args, **kwargs)

class VariantParameterLearner:
    def __new__(cls, *args, **kwargs):
        from .variant import VariantParameterLearner as _VPL
        return _VPL(*args, **kwargs)

class VariantParams:
    def __new__(cls, *args, **kwargs):
        from .variant import VariantParams as _VP
        return _VP(*args, **kwargs)

class SimulationResult:
    def __new__(cls, *args, **kwargs):
        from .result import SimulationResult as _SR
        return _SR(*args, **kwargs)
