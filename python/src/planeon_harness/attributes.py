"""Stable harness semantic attributes with conservative redaction defaults."""

from __future__ import annotations

import math
import re
from dataclasses import dataclass
from types import MappingProxyType
from typing import Iterable, Mapping, TypeAlias

from planeon_harness.context import HarnessContext


TELEMETRY_SCHEMA_VERSION = "1.0.0"
SEMANTIC_ATTRIBUTE_KEYS = MappingProxyType(
    {
        "schema_version": "harness.telemetry.schema.version",
        "tenant_id": "harness.tenant.id",
        "organization_id": "harness.organization.id",
        "harness_id": "harness.id",
        "plane_id": "harness.plane.id",
        "operation_id": "harness.operation.id",
        "correlation_id": "harness.correlation.id",
        "operation_name": "harness.operation.name",
        "operation_kind": "harness.operation.kind",
        "outcome": "harness.operation.outcome",
        "error_type": "error.type",
        "exception_type": "exception.type",
    }
)
SENSITIVE_KEY_SEGMENTS = frozenset(
    {
        "api_key",
        "authorization",
        "body",
        "completion",
        "content",
        "cookie",
        "credential",
        "message",
        "password",
        "payload",
        "prompt",
        "secret",
        "token",
    }
)
OPERATION_KINDS = frozenset({"INTERNAL", "CLIENT", "SERVER", "PRODUCER", "CONSUMER"})
OUTCOMES = frozenset({"success", "error"})
MAX_ATTRIBUTE_STRING_LENGTH = 256

_ATTRIBUTE_KEY = re.compile(r"^[a-z][a-z0-9_]*(?:\.[a-z][a-z0-9_]*)+$")
_OPERATION_NAME = re.compile(r"^[a-z][a-z0-9_.-]{0,127}$")
_SAFE_STRING = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/-]{0,255}$")
_CUSTOM_PREFIX = "harness.label."

AttributeScalar: TypeAlias = str | bool | int | float
AttributeValue: TypeAlias = AttributeScalar | tuple[AttributeScalar, ...]


class AttributeValidationError(ValueError):
    """Raised for malformed required semantic attributes."""


@dataclass(frozen=True, slots=True)
class SanitizedAttributes:
    """Immutable accepted attributes plus a non-identifying removal count."""

    values: Mapping[str, AttributeValue]
    dropped_count: int


def validate_operation_name(value: str) -> str:
    if _OPERATION_NAME.fullmatch(value) is None:
        raise AttributeValidationError(
            "operation name must be lowercase, non-empty, and at most 128 safe characters"
        )
    return value


def validate_operation_kind(value: str) -> str:
    if value not in OPERATION_KINDS:
        raise AttributeValidationError(f"unknown operation kind: {value}")
    return value


def _key_is_sensitive(key: str) -> bool:
    components = set(key.split("."))
    tokens = set(re.split(r"[._]", key))
    return any(segment in components or segment in tokens for segment in SENSITIVE_KEY_SEGMENTS)


def _key_is_allowed(key: str) -> bool:
    return key in SEMANTIC_ATTRIBUTE_KEYS.values() or key.startswith(_CUSTOM_PREFIX)


def _sanitize_scalar(value: object) -> AttributeScalar | None:
    if isinstance(value, bool):
        return value
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return value if math.isfinite(value) else None
    if (
        isinstance(value, str)
        and len(value) <= MAX_ATTRIBUTE_STRING_LENGTH
        and _SAFE_STRING.fullmatch(value) is not None
    ):
        return value
    return None


def _sanitize_value(value: object) -> AttributeValue | None:
    scalar = _sanitize_scalar(value)
    if scalar is not None:
        return scalar
    if isinstance(value, (list, tuple)) and value:
        sanitized = tuple(_sanitize_scalar(item) for item in value)
        if all(item is not None for item in sanitized):
            types = {type(item) for item in sanitized}
            if len(types) == 1:
                return tuple(item for item in sanitized if item is not None)
    return None


def sanitize_attributes(attributes: Mapping[str, object] | None) -> SanitizedAttributes:
    """Allow only stable harness keys, safe labels, and scalar OTel values.

    Unknown, sensitive, overlong, non-finite, nested, or heterogeneous values
    are dropped without copying their values into diagnostics.
    """

    accepted: dict[str, AttributeValue] = {}
    dropped_count = 0
    sortable: list[tuple[str, object]] = []
    for key, value in (attributes or {}).items():
        if not isinstance(key, str):
            dropped_count += 1
            continue
        sortable.append((key, value))
    for key, value in sorted(sortable):
        if (
            _ATTRIBUTE_KEY.fullmatch(key) is None
            or _key_is_sensitive(key)
            or not _key_is_allowed(key)
        ):
            dropped_count += 1
            continue
        sanitized = _sanitize_value(value)
        if sanitized is None:
            dropped_count += 1
            continue
        accepted[key] = sanitized
    return SanitizedAttributes(
        values=MappingProxyType(dict(sorted(accepted.items()))),
        dropped_count=dropped_count,
    )


def context_attributes(
    context: HarnessContext,
    *,
    operation_name: str,
    operation_kind: str,
    outcome: str,
) -> dict[str, AttributeValue]:
    """Build required semantic attributes from an admitted context."""

    validate_operation_name(operation_name)
    validate_operation_kind(operation_kind)
    if outcome not in OUTCOMES:
        raise AttributeValidationError(f"unknown operation outcome: {outcome}")
    attributes: dict[str, AttributeValue] = {
        SEMANTIC_ATTRIBUTE_KEYS["schema_version"]: TELEMETRY_SCHEMA_VERSION,
        SEMANTIC_ATTRIBUTE_KEYS["operation_name"]: operation_name,
        SEMANTIC_ATTRIBUTE_KEYS["operation_kind"]: operation_kind,
        SEMANTIC_ATTRIBUTE_KEYS["outcome"]: outcome,
    }
    identity_fields: Iterable[str] = (
        "tenant_id",
        "organization_id",
        "harness_id",
        "plane_id",
        "operation_id",
        "correlation_id",
    )
    for field_name in identity_fields:
        value = getattr(context, field_name)
        if value is not None:
            attributes[SEMANTIC_ATTRIBUTE_KEYS[field_name]] = value
    return dict(sorted(attributes.items()))
