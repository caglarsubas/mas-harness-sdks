"""Bounded CrewAI crew invocation adapter."""

from __future__ import annotations

from typing import Any

from planeon_harness.decorators import SpanSink

from ._base import invoke_async, invoke_sync, require_integration, require_methods


class CrewAIAdapter:
    """Expose only admitted crew kickoff methods."""

    __slots__ = ("_crew", "_sink")

    def __init__(self, crew: object, sink: SpanSink | None) -> None:
        self._crew = crew
        self._sink = sink

    def kickoff(self, *args: Any, **kwargs: Any) -> Any:
        return invoke_sync(
            self._crew.kickoff,
            "harness.integration.crewai.kickoff",
            self._sink,
            args,
            kwargs,
        )

    async def kickoff_async(self, *args: Any, **kwargs: Any) -> Any:
        return await invoke_async(
            self._crew.kickoff_async,
            "harness.integration.crewai.kickoff_async",
            self._sink,
            args,
            kwargs,
        )


def instrument_crewai(
    crew: object,
    *,
    sink: SpanSink | None = None,
) -> CrewAIAdapter:
    """Validate CrewAI availability and return a side-effect-free adapter."""

    require_integration("crewai")
    require_methods("crewai", crew, ("kickoff", "kickoff_async"))
    return CrewAIAdapter(crew, sink)
