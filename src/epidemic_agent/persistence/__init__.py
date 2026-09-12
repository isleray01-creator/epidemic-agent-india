from .state_store import SecurityError

def get_state_store():
    from .state_store import get_state_store as _fn
    return _fn()

def save_state(*args, **kwargs):
    from .state_store import save_state as _fn
    return _fn(*args, **kwargs)

def load_state(*args, **kwargs):
    from .state_store import load_state as _fn
    return _fn(*args, **kwargs)

class TrustedStateStore:
    def __new__(cls, *args, **kwargs):
        from .state_store import TrustedStateStore as _TSS
        return _TSS(*args, **kwargs)
