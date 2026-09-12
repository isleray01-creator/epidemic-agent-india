from __future__ import annotations

import logging
from collections.abc import Callable

from langchain_core.tools import BaseTool, StructuredTool

logger = logging.getLogger(__name__)


class ToolRegistry:
    def __init__(self):
        self._tools: dict[str, BaseTool] = {}
        self._schemas: dict[str, dict] = {}

    def register(self, func: Callable, name: str | None = None, description: str | None = None) -> BaseTool:
        tool_name = name or func.__name__
        if tool_name in self._tools:
            logger.warning(f"Tool {tool_name} already registered, overwriting")

        if not hasattr(func, "lc_tool"):
            decorated = StructuredTool.from_function(
                func=func,
                name=tool_name,
                description=description or func.__doc__ or "",
            )
        else:
            decorated = func

        self._tools[tool_name] = decorated
        self._schemas[tool_name] = {
            "name": tool_name,
            "description": description or func.__doc__ or "",
            "parameters": decorated.args_schema.model_json_schema() if decorated.args_schema else {},
        }
        logger.debug(f"Registered tool: {tool_name}")
        return decorated

    def get(self, name: str) -> BaseTool | None:
        return self._tools.get(name)

    def get_all(self) -> list[BaseTool]:
        return list(self._tools.values())

    def get_schemas(self) -> list[dict]:
        return list(self._schemas.values())

    def get_tool_names(self) -> list[str]:
        return list(self._tools.keys())


_registry: ToolRegistry | None = None


def get_tool_registry() -> ToolRegistry:
    global _registry
    if _registry is None:
        _registry = ToolRegistry()
    return _registry


def register_tool(name: str | None = None, description: str | None = None):
    def decorator(func: Callable) -> BaseTool:
        return get_tool_registry().register(func, name, description)
    return decorator
