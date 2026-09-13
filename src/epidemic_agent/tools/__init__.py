_tools = {}
_loaded = set()

MODULE_MAP = {
    "fetch_epidemic_data": ("data_fetcher", "fetch_epidemic_data"),
    "fetch_vaccination_data": ("data_fetcher", "fetch_vaccination_data"),
    "fetch_demographics": ("data_fetcher", "fetch_demographics"),
    "simulate_spread": ("simulator", "simulate_spread"),
    "detect_variant_shock": ("shock_detector", "detect_variant_shock"),
    "evaluate_contact_tracing": ("policy_eval", "evaluate_contact_tracing"),
    "evaluate_policy": ("policy_eval", "evaluate_policy"),
    "calculate_objective": ("objective", "calculate_objective"),
}

CLASS_MAP = {
    "VariantShockDetector": ("shock_detector", "VariantShockDetector"),
    "ObjectiveFunction": ("objective", "ObjectiveFunction"),
    "ToolRegistry": ("registry", "ToolRegistry"),
}

FUNC_MAP = {
    "get_tool_registry": ("registry", "get_tool_registry"),
    "register_tool": ("registry", "register_tool"),
}


def _load_module(module_name):
    if module_name not in _loaded:
        import importlib
        importlib.import_module(f"epidemic_agent.tools.{module_name}")
        _loaded.add(module_name)


def _get_tool(name):
    if name not in _tools:
        mapping = MODULE_MAP.get(name) or CLASS_MAP.get(name) or FUNC_MAP.get(name)
        if mapping is None:
            raise ValueError(f"Unknown tool: {name}")
        mod_name, attr = mapping
        _load_module(mod_name)
        import importlib
        mod = importlib.import_module(f"epidemic_agent.tools.{mod_name}")
        _tools[name] = getattr(mod, attr)
    return _tools[name]


class _ToolProxy:
    def __init__(self, name):
        self._tool_name = name

    def _real(self):
        return _get_tool(self._tool_name)

    def __call__(self, *a, **kw):
        return self._real()(*a, **kw)

    def __getattr__(self, attr):
        return getattr(self._real(), attr)

    def __repr__(self):
        return f"<lazy tool: {self._tool_name}>"


fetch_epidemic_data = _ToolProxy("fetch_epidemic_data")
fetch_vaccination_data = _ToolProxy("fetch_vaccination_data")
fetch_demographics = _ToolProxy("fetch_demographics")
simulate_spread = _ToolProxy("simulate_spread")
detect_variant_shock = _ToolProxy("detect_variant_shock")
evaluate_contact_tracing = _ToolProxy("evaluate_contact_tracing")
evaluate_policy = _ToolProxy("evaluate_policy")
calculate_objective = _ToolProxy("calculate_objective")

VariantShockDetector = type("VariantShockDetector", (), {
    "__new__": lambda cls, *a, **kw: _get_tool("VariantShockDetector")(*a, **kw)
})
ObjectiveFunction = type("ObjectiveFunction", (), {
    "__new__": lambda cls, *a, **kw: _get_tool("ObjectiveFunction")(*a, **kw)
})
ToolRegistry = type("ToolRegistry", (), {
    "__new__": lambda cls, *a, **kw: _get_tool("ToolRegistry")(*a, **kw)
})


def get_tool_registry(*a, **kw):
    return _get_tool("get_tool_registry")(*a, **kw)

def register_tool(*a, **kw):
    return _get_tool("register_tool")(*a, **kw)
