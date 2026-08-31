"""Shared fail-closed machinery for optional framework adapters."""

from __future__ import annotations

import importlib
import inspect
from collections.abc import Awaitable, Callable, Mapping
from dataclasses import dataclass
from types import MappingProxyType, ModuleType
from typing import Any, TypeVar, cast

from planeon_harness.decorators import NullSpanSink, SpanSink, instrument


T = TypeVar("T")


@dataclass(frozen=True, slots=True)
class IntegrationSpec:
    """One immutable package and import compatibility declaration."""

    extra: str
    distribution: str
    import_name: str
    requirement: str
    baseline_version: str
    source_url: str
    verification: str = "OFFLINE_FAKE_SURFACE_ONLY"


class IntegrationUnavailableError(ImportError):
    """Raised when an explicitly requested optional framework is unavailable."""

    code = "OPTIONAL_INTEGRATION_UNAVAILABLE"

    def __init__(self, integration: str, extra: str) -> None:
        self.integration = integration
        self.extra = extra
        super().__init__(
            f"optional integration {integration!r} is unavailable; install extra {extra!r}"
        )


class IntegrationContractError(TypeError):
    """Raised when a caller-supplied object lacks the bounded adapter surface."""

    code = "INVALID_INTEGRATION_SURFACE"

    def __init__(self, integration: str, detail: str) -> None:
        self.integration = integration
        super().__init__(f"invalid {integration!r} integration surface: {detail}")


INTEGRATION_SPECS: Mapping[str, IntegrationSpec] = MappingProxyType(
    {
        "crewai": IntegrationSpec(
            extra="crewai",
            distribution="crewai",
            import_name="crewai",
            requirement="crewai>=1.15,<2",
            baseline_version="1.15.18",
            source_url="https://pypi.org/project/crewai/1.15.18/",
        ),
        "langchain": IntegrationSpec(
            extra="langchain",
            distribution="langchain-core",
            import_name="langchain_core",
            requirement="langchain-core>=1.6,<2",
            baseline_version="1.6.1",
            source_url="https://pypi.org/project/langchain-core/1.6.1/",
        ),
        "langgraph": IntegrationSpec(
            extra="langgraph",
            distribution="langgraph",
            import_name="langgraph",
            requirement="langgraph>=1.2,<2",
            baseline_version="1.2.11",
            source_url="https://pypi.org/project/langgraph/1.2.11/",
        ),
        "mcp": IntegrationSpec(
            extra="mcp",
            distribution="mcp",
            import_name="mcp",
            requirement="mcp>=2.1,<3",
            baseline_version="2.1.1",
            source_url="https://pypi.org/project/mcp/2.1.1/",
        ),
        "semantic_kernel": IntegrationSpec(
            extra="semantic-kernel",
            distribution="semantic-kernel",
            import_name="semantic_kernel",
            requirement="semantic-kernel>=1.44,<2",
            baseline_version="1.44.1",
            source_url="https://pypi.org/project/semantic-kernel/1.44.1/",
        ),
    }
)


def require_integration(integration: str) -> ModuleType:
    """Import exactly one declared framework after an explicit factory call."""

    spec = INTEGRATION_SPECS.get(integration)
    if spec is None:
        raise IntegrationContractError(integration, "integration is not declared")
    try:
        return importlib.import_module(spec.import_name)
    except ImportError as exc:
        raise IntegrationUnavailableError(integration, spec.extra) from exc


def require_methods(integration: str, target: object, methods: tuple[str, ...]) -> None:
    """Validate the complete bounded surface without invoking the target."""

    missing = tuple(name for name in methods if not callable(getattr(target, name, None)))
    if missing:
        raise IntegrationContractError(
            integration,
            "missing callable methods: " + ", ".join(missing),
        )


def invoke_sync(
    method: Callable[..., T],
    operation_name: str,
    sink: SpanSink | None,
    args: tuple[Any, ...],
    kwargs: dict[str, Any],
) -> T:
    """Instrument one explicit synchronous delegation without inspecting data."""

    if inspect.iscoroutinefunction(method):
        raise IntegrationContractError(operation_name, "synchronous method is asynchronous")
    wrapped = cast(Callable[..., T], instrument(
        operation_name,
        operation_kind="CLIENT",
        sink=sink or NullSpanSink(),
    )(method))
    result = wrapped(*args, **kwargs)
    if inspect.isawaitable(result):
        close = getattr(result, "close", None)
        if callable(close):
            close()
        raise IntegrationContractError(operation_name, "synchronous method returned an awaitable")
    return result


async def invoke_async(
    method: Callable[..., Awaitable[T]],
    operation_name: str,
    sink: SpanSink | None,
    args: tuple[Any, ...],
    kwargs: dict[str, Any],
) -> T:
    """Instrument one explicit asynchronous delegation without inspecting data."""

    async def delegate() -> T:
        result = method(*args, **kwargs)
        if not inspect.isawaitable(result):
            raise IntegrationContractError(operation_name, "asynchronous method returned a value")
        return await result

    wrapped = cast(
        Callable[[], Awaitable[T]],
        instrument(
            operation_name,
            operation_kind="CLIENT",
            sink=sink or NullSpanSink(),
        )(delegate),
    )
    return await wrapped()
