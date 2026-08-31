"""Dependency-free wrappers for caller-supplied vector search callables."""

from __future__ import annotations

import inspect
from collections.abc import Awaitable, Callable
from typing import Any, TypeVar, cast

from planeon_harness.decorators import NullSpanSink, SpanSink, instrument

from ._base import IntegrationContractError


T = TypeVar("T")


def instrument_vector_search(
    search: Callable[..., T],
    *,
    sink: SpanSink | None = None,
) -> Callable[..., T]:
    """Wrap a synchronous search callable without selecting a vector vendor."""

    if not callable(search) or inspect.iscoroutinefunction(search):
        raise IntegrationContractError("vector", "search must be synchronous")
    return cast(
        Callable[..., T],
        instrument(
            "harness.integration.vector.search",
            operation_kind="CLIENT",
            sink=sink or NullSpanSink(),
        )(search),
    )


def instrument_async_vector_search(
    search: Callable[..., Awaitable[T]],
    *,
    sink: SpanSink | None = None,
) -> Callable[..., Awaitable[T]]:
    """Wrap an asynchronous search callable without selecting a vector vendor."""

    if not callable(search) or not inspect.iscoroutinefunction(search):
        raise IntegrationContractError("vector", "search must be asynchronous")
    return cast(
        Callable[..., Awaitable[T]],
        instrument(
            "harness.integration.vector.asearch",
            operation_kind="CLIENT",
            sink=sink or NullSpanSink(),
        )(search),
    )
