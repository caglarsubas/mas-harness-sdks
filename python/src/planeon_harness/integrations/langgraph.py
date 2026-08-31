"""Bounded LangGraph graph invocation adapter."""

from __future__ import annotations

from typing import Any

from planeon_harness.decorators import SpanSink

from ._base import invoke_async, invoke_sync, require_integration, require_methods


class LangGraphAdapter:
    """Expose only non-streaming graph invocation methods."""

    __slots__ = ("_graph", "_sink")

    def __init__(self, graph: object, sink: SpanSink | None) -> None:
        self._graph = graph
        self._sink = sink

    def invoke(self, *args: Any, **kwargs: Any) -> Any:
        return invoke_sync(
            self._graph.invoke,
            "harness.integration.langgraph.invoke",
            self._sink,
            args,
            kwargs,
        )

    async def ainvoke(self, *args: Any, **kwargs: Any) -> Any:
        return await invoke_async(
            self._graph.ainvoke,
            "harness.integration.langgraph.ainvoke",
            self._sink,
            args,
            kwargs,
        )


def instrument_langgraph(
    graph: object,
    *,
    sink: SpanSink | None = None,
) -> LangGraphAdapter:
    """Validate LangGraph availability and return a side-effect-free adapter."""

    require_integration("langgraph")
    require_methods("langgraph", graph, ("invoke", "ainvoke"))
    return LangGraphAdapter(graph, sink)
