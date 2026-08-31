"""Dependency-free sync and async harness span instrumentation."""

from __future__ import annotations

import inspect
import json
import secrets
import time
from dataclasses import dataclass
from functools import wraps
from types import MappingProxyType
from typing import Any, Awaitable, Callable, Mapping, ParamSpec, Protocol, TypeVar, cast

from planeon_harness.attributes import (
    AttributeValue,
    SEMANTIC_ATTRIBUTE_KEYS,
    context_attributes,
    sanitize_attributes,
    validate_operation_kind,
    validate_operation_name,
)
from planeon_harness.context import HarnessContext, current_context, use_context


P = ParamSpec("P")
R = TypeVar("R")
SPAN_SCHEMA_VERSION = "harness.telemetry.span/v1"


class SpanSink(Protocol):
    """Minimal local sink contract; adapters decide if and where to export."""

    def emit(self, record: SpanRecord) -> None:
        """Consume a completed immutable record."""


class NullSpanSink:
    """Default sink that performs no I/O and retains no telemetry."""

    def emit(self, record: SpanRecord) -> None:
        del record


class InMemorySpanSink:
    """Test and local-development sink with no external side effects."""

    def __init__(self) -> None:
        self.records: list[SpanRecord] = []

    def emit(self, record: SpanRecord) -> None:
        self.records.append(record)


@dataclass(frozen=True, slots=True)
class SpanEvent:
    name: str
    time_unix_nano: str
    attributes: Mapping[str, AttributeValue]

    def to_dict(self) -> dict[str, object]:
        return {
            "attributes": dict(sorted(self.attributes.items())),
            "name": self.name,
            "timeUnixNano": self.time_unix_nano,
        }


@dataclass(frozen=True, slots=True)
class SpanRecord:
    """Small OpenTelemetry-compatible span vector without an exporter."""

    name: str
    kind: str
    trace_id: str
    span_id: str
    parent_span_id: str | None
    trace_flags: str
    start_time_unix_nano: str
    end_time_unix_nano: str
    status_code: str
    attributes: Mapping[str, AttributeValue]
    events: tuple[SpanEvent, ...] = ()
    dropped_attributes_count: int = 0

    def to_dict(self) -> dict[str, object]:
        return {
            "attributes": dict(sorted(self.attributes.items())),
            "droppedAttributesCount": self.dropped_attributes_count,
            "endTimeUnixNano": self.end_time_unix_nano,
            "events": [event.to_dict() for event in self.events],
            "kind": self.kind,
            "name": self.name,
            "parentSpanId": self.parent_span_id,
            "schemaVersion": SPAN_SCHEMA_VERSION,
            "spanId": self.span_id,
            "startTimeUnixNano": self.start_time_unix_nano,
            "status": {"code": self.status_code},
            "traceFlags": self.trace_flags,
            "traceId": self.trace_id,
        }

    def canonical_json(self) -> str:
        return json.dumps(self.to_dict(), sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _default_error_type(error: BaseException) -> str:
    name = type(error).__name__
    pieces: list[str] = []
    for character in name:
        if character.isupper() and pieces:
            pieces.append("_")
        pieces.append(character.lower())
    return "".join(pieces)


def _emit(sink: SpanSink, record: SpanRecord, *, strict_sink: bool) -> None:
    try:
        sink.emit(record)
    except Exception:
        if strict_sink:
            raise


def _classify_error(
    classifier: Callable[[BaseException], str],
    error: BaseException,
) -> str:
    """Return a safe type without allowing telemetry code to mask the failure."""

    try:
        value = classifier(error)
    except BaseException:
        return "error"
    return value if isinstance(value, str) else "error"


def _record(
    *,
    operation_name: str,
    operation_kind: str,
    context: HarnessContext,
    parent_span_id: str | None,
    start: int,
    end: int,
    outcome: str,
    extra_attributes: Mapping[str, object] | None,
    error_type: str | None,
) -> SpanRecord:
    base = context_attributes(
        context,
        operation_name=operation_name,
        operation_kind=operation_kind,
        outcome=outcome,
    )
    sanitized = sanitize_attributes(extra_attributes)
    base.update(sanitized.values)
    events: tuple[SpanEvent, ...] = ()
    if error_type is not None:
        safe_error = sanitize_attributes({SEMANTIC_ATTRIBUTE_KEYS["error_type"]: error_type})
        safe_exception = sanitize_attributes(
            {SEMANTIC_ATTRIBUTE_KEYS["exception_type"]: error_type}
        )
        base.update(safe_error.values)
        events = (
            SpanEvent(
                name="exception",
                time_unix_nano=str(end),
                attributes=safe_exception.values,
            ),
        )
    return SpanRecord(
        name=operation_name,
        kind=operation_kind,
        trace_id=context.trace_id,
        span_id=context.span_id,
        parent_span_id=parent_span_id,
        trace_flags=context.trace_flags,
        start_time_unix_nano=str(start),
        end_time_unix_nano=str(end),
        status_code="ERROR" if outcome == "error" else "OK",
        attributes=MappingProxyType(dict(sorted(base.items()))),
        events=events,
        dropped_attributes_count=sanitized.dropped_count,
    )


def instrument(
    operation_name: str,
    *,
    operation_kind: str = "INTERNAL",
    attributes: Mapping[str, object] | None = None,
    sink: SpanSink | None = None,
    clock_ns: Callable[[], int] = time.time_ns,
    span_id_factory: Callable[[], str] = lambda: secrets.token_hex(8),
    error_type: Callable[[BaseException], str] = _default_error_type,
    strict_sink: bool = False,
) -> Callable[[Callable[P, R] | Callable[P, Awaitable[R]]], Callable[P, R] | Callable[P, Awaitable[R]]]:
    """Instrument a callable without recording arguments, results, or messages."""

    validate_operation_name(operation_name)
    validate_operation_kind(operation_kind)
    destination = sink or NullSpanSink()

    def decorate(
        function: Callable[P, R] | Callable[P, Awaitable[R]],
    ) -> Callable[P, R] | Callable[P, Awaitable[R]]:
        if inspect.iscoroutinefunction(function):

            @wraps(function)
            async def async_wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
                parent = current_context()
                active = (
                    parent.child(span_id=span_id_factory())
                    if parent is not None
                    else HarnessContext.create(span_id=span_id_factory())
                )
                started = clock_ns()
                try:
                    with use_context(active):
                        result = await cast(Callable[P, Awaitable[R]], function)(*args, **kwargs)
                except BaseException as exc:
                    ended = clock_ns()
                    record = _record(
                        operation_name=operation_name,
                        operation_kind=operation_kind,
                        context=active,
                        parent_span_id=parent.span_id if parent is not None else None,
                        start=started,
                        end=ended,
                        outcome="error",
                        extra_attributes=attributes,
                        error_type=_classify_error(error_type, exc),
                    )
                    _emit(destination, record, strict_sink=False)
                    raise
                ended = clock_ns()
                _emit(
                    destination,
                    _record(
                        operation_name=operation_name,
                        operation_kind=operation_kind,
                        context=active,
                        parent_span_id=parent.span_id if parent is not None else None,
                        start=started,
                        end=ended,
                        outcome="success",
                        extra_attributes=attributes,
                        error_type=None,
                    ),
                    strict_sink=strict_sink,
                )
                return result

            return async_wrapper

        @wraps(function)
        def sync_wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            parent = current_context()
            active = (
                parent.child(span_id=span_id_factory())
                if parent is not None
                else HarnessContext.create(span_id=span_id_factory())
            )
            started = clock_ns()
            try:
                with use_context(active):
                    result = cast(Callable[P, R], function)(*args, **kwargs)
            except BaseException as exc:
                ended = clock_ns()
                record = _record(
                    operation_name=operation_name,
                    operation_kind=operation_kind,
                    context=active,
                    parent_span_id=parent.span_id if parent is not None else None,
                    start=started,
                    end=ended,
                    outcome="error",
                    extra_attributes=attributes,
                    error_type=_classify_error(error_type, exc),
                )
                _emit(destination, record, strict_sink=False)
                raise
            ended = clock_ns()
            _emit(
                destination,
                _record(
                    operation_name=operation_name,
                    operation_kind=operation_kind,
                    context=active,
                    parent_span_id=parent.span_id if parent is not None else None,
                    start=started,
                    end=ended,
                    outcome="success",
                    extra_attributes=attributes,
                    error_type=None,
                ),
                strict_sink=strict_sink,
            )
            return result

        return sync_wrapper

    return decorate
