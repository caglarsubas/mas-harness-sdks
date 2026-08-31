"""Bounded LangChain runnable invocation adapter."""

from __future__ import annotations

from typing import Any

from planeon_harness.decorators import SpanSink

from ._base import invoke_async, invoke_sync, require_integration, require_methods


class LangChainRunnableAdapter:
    """Expose only the admitted runnable invocation methods."""

    __slots__ = ("_runnable", "_sink")

    def __init__(self, runnable: object, sink: SpanSink | None) -> None:
        self._runnable = runnable
        self._sink = sink

    def invoke(self, *args: Any, **kwargs: Any) -> Any:
        return invoke_sync(
            self._runnable.invoke,
            "harness.integration.langchain.invoke",
            self._sink,
            args,
            kwargs,
        )

    async def ainvoke(self, *args: Any, **kwargs: Any) -> Any:
        return await invoke_async(
            self._runnable.ainvoke,
            "harness.integration.langchain.ainvoke",
            self._sink,
            args,
            kwargs,
        )


def instrument_langchain_runnable(
    runnable: object,
    *,
    sink: SpanSink | None = None,
) -> LangChainRunnableAdapter:
    """Validate LangChain availability and return a side-effect-free adapter."""

    require_integration("langchain")
    require_methods("langchain", runnable, ("invoke", "ainvoke"))
    return LangChainRunnableAdapter(runnable, sink)
