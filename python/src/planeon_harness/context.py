"""Tenant-neutral harness context and W3C trace-context propagation."""

from __future__ import annotations

import re
import secrets
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass
from typing import Iterator, Mapping


TRACEPARENT_HEADER = "traceparent"
IDENTITY_HEADERS = {
    "tenant_id": "x-harness-tenant-id",
    "organization_id": "x-harness-organization-id",
    "harness_id": "x-harness-harness-id",
    "plane_id": "x-harness-plane-id",
    "operation_id": "x-harness-operation-id",
    "correlation_id": "x-harness-correlation-id",
}

_TRACE_ID = re.compile(r"^[0-9a-f]{32}$")
_SPAN_ID = re.compile(r"^[0-9a-f]{16}$")
_TRACE_FLAGS = re.compile(r"^[0-9a-f]{2}$")
_OPAQUE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")
_ZERO_TRACE_ID = "0" * 32
_ZERO_SPAN_ID = "0" * 16
_CURRENT_CONTEXT: ContextVar[HarnessContext | None] = ContextVar(
    "planeon_harness_context",
    default=None,
)


class ContextValidationError(ValueError):
    """Raised when context identity or trace material is malformed."""


def _validate_trace_id(value: str) -> str:
    if _TRACE_ID.fullmatch(value) is None or value == _ZERO_TRACE_ID:
        raise ContextValidationError("trace_id must be 32 lowercase non-zero hexadecimal characters")
    return value


def _validate_span_id(value: str) -> str:
    if _SPAN_ID.fullmatch(value) is None or value == _ZERO_SPAN_ID:
        raise ContextValidationError("span_id must be 16 lowercase non-zero hexadecimal characters")
    return value


def _validate_trace_flags(value: str) -> str:
    if _TRACE_FLAGS.fullmatch(value) is None:
        raise ContextValidationError("trace_flags must be two lowercase hexadecimal characters")
    return value


def _validate_opaque_id(name: str, value: str | None) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str) or _OPAQUE_ID.fullmatch(value) is None:
        raise ContextValidationError(
            f"{name} must be an opaque 1-128 character identifier without whitespace"
        )
    return value


@dataclass(frozen=True, slots=True)
class HarnessContext:
    """Validated context for one active span.

    Tenant and organization identifiers are boundary claims. Carrier extraction
    ignores them unless the caller explicitly marks the carrier as trusted.
    """

    trace_id: str
    span_id: str
    trace_flags: str = "00"
    tenant_id: str | None = None
    organization_id: str | None = None
    harness_id: str | None = None
    plane_id: str | None = None
    operation_id: str | None = None
    correlation_id: str | None = None

    def __post_init__(self) -> None:
        _validate_trace_id(self.trace_id)
        _validate_span_id(self.span_id)
        _validate_trace_flags(self.trace_flags)
        for name in IDENTITY_HEADERS:
            _validate_opaque_id(name, getattr(self, name))

    @classmethod
    def create(
        cls,
        *,
        trace_id: str | None = None,
        span_id: str | None = None,
        trace_flags: str = "00",
        tenant_id: str | None = None,
        organization_id: str | None = None,
        harness_id: str | None = None,
        plane_id: str | None = None,
        operation_id: str | None = None,
        correlation_id: str | None = None,
    ) -> HarnessContext:
        """Create a context with cryptographically random trace IDs by default."""

        return cls(
            trace_id=secrets.token_hex(16) if trace_id is None else trace_id,
            span_id=secrets.token_hex(8) if span_id is None else span_id,
            trace_flags=trace_flags,
            tenant_id=tenant_id,
            organization_id=organization_id,
            harness_id=harness_id,
            plane_id=plane_id,
            operation_id=operation_id,
            correlation_id=correlation_id,
        )

    def child(self, *, span_id: str | None = None) -> HarnessContext:
        """Return a child span context while preserving admitted identity."""

        return HarnessContext(
            trace_id=self.trace_id,
            span_id=secrets.token_hex(8) if span_id is None else span_id,
            trace_flags=self.trace_flags,
            tenant_id=self.tenant_id,
            organization_id=self.organization_id,
            harness_id=self.harness_id,
            plane_id=self.plane_id,
            operation_id=self.operation_id,
            correlation_id=self.correlation_id,
        )


def format_traceparent(context: HarnessContext) -> str:
    """Serialize the supported W3C Trace Context version 00 form."""

    return f"00-{context.trace_id}-{context.span_id}-{context.trace_flags}"


def parse_traceparent(value: str) -> tuple[str, str, str]:
    """Parse a strict version 00 W3C traceparent value."""

    parts = value.split("-")
    if len(parts) != 4 or parts[0] != "00":
        raise ContextValidationError("only the four-field W3C traceparent version 00 is supported")
    trace_id, span_id, trace_flags = parts[1:]
    return (
        _validate_trace_id(trace_id),
        _validate_span_id(span_id),
        _validate_trace_flags(trace_flags),
    )


def _normalize_carrier(carrier: Mapping[str, str]) -> dict[str, str]:
    normalized: dict[str, str] = {}
    for raw_name, raw_value in carrier.items():
        if not isinstance(raw_name, str) or not isinstance(raw_value, str):
            raise ContextValidationError("carrier names and values must be strings")
        name = raw_name.lower()
        if name in normalized:
            raise ContextValidationError(f"carrier contains a case-insensitive duplicate: {name}")
        if "\r" in raw_value or "\n" in raw_value:
            raise ContextValidationError(f"carrier value contains a line break: {name}")
        normalized[name] = raw_value
    return normalized


def inject_context(
    context: HarnessContext,
    carrier: Mapping[str, str] | None = None,
    *,
    include_identity: bool = False,
) -> dict[str, str]:
    """Return a carrier containing trace context and optionally trusted identity."""

    result = _normalize_carrier(carrier or {})
    result[TRACEPARENT_HEADER] = format_traceparent(context)
    if include_identity:
        for field_name, header_name in IDENTITY_HEADERS.items():
            value = getattr(context, field_name)
            if value is not None:
                result[header_name] = value
    return dict(sorted(result.items()))


def extract_context(
    carrier: Mapping[str, str],
    *,
    trust_identity: bool = False,
    strict: bool = False,
) -> HarnessContext | None:
    """Extract a context, ignoring invalid input unless ``strict`` is true.

    Identity headers are deliberately ignored by default. A service must first
    authenticate its transport boundary before setting ``trust_identity=True``.
    """

    try:
        normalized = _normalize_carrier(carrier)
        traceparent = normalized.get(TRACEPARENT_HEADER)
        if traceparent is None:
            return None
        trace_id, span_id, trace_flags = parse_traceparent(traceparent)
        identity = {
            field_name: normalized.get(header_name) if trust_identity else None
            for field_name, header_name in IDENTITY_HEADERS.items()
        }
        return HarnessContext(
            trace_id=trace_id,
            span_id=span_id,
            trace_flags=trace_flags,
            **identity,
        )
    except ContextValidationError:
        if strict:
            raise
        return None


def current_context(*, required: bool = False) -> HarnessContext | None:
    """Return the current task-local context."""

    context = _CURRENT_CONTEXT.get()
    if required and context is None:
        raise ContextValidationError("no harness context is active")
    return context


@contextmanager
def use_context(context: HarnessContext) -> Iterator[HarnessContext]:
    """Bind context to this synchronous or asynchronous Python task scope."""

    token = _CURRENT_CONTEXT.set(context)
    try:
        yield context
    finally:
        _CURRENT_CONTEXT.reset(token)
