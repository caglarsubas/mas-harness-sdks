"""Pure budget evaluation for runtime admission."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from types import MappingProxyType
from typing import Mapping

from planeon_harness.runtime.canonical import document_digest, require_sha256


LIMIT_TO_OBSERVED = (
    ("maxConcurrentTasks", "concurrentTasks", "CONCURRENT_TASKS", 1, 1024, 0, 1025),
    ("maxTaskSeconds", "taskSeconds", "TASK_SECONDS", 1, 86400, 0, 86401),
    ("maxRetries", "retries", "RETRIES", 0, 100, 0, 101),
    ("maxToolCalls", "toolCalls", "TOOL_CALLS", 0, 10000, 0, 10001),
    ("maxModelTokens", "modelTokens", "MODEL_TOKENS", 0, 10000000, 0, 10000001),
)


class BudgetValidationError(ValueError):
    """Raised for incomplete, malformed, or mismatched budget input."""


def _bounded_int(value: object, minimum: int, maximum: int, field: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or not minimum <= value <= maximum:
        raise BudgetValidationError(f"{field} must be an integer in [{minimum}, {maximum}]")
    return value


def _timestamp(value: datetime) -> str:
    if not isinstance(value, datetime) or value.tzinfo is None:
        raise BudgetValidationError("recorded_at must be timezone-aware")
    utc = value.astimezone(timezone.utc)
    if utc.microsecond:
        raise BudgetValidationError("recorded_at must have whole-second precision")
    return utc.strftime("%Y-%m-%dT%H:%M:%SZ")


@dataclass(frozen=True, slots=True)
class BudgetEvaluation:
    within_budget: bool
    exceeded_dimensions: tuple[str, ...]
    document: Mapping[str, object]
    digest: str


def evaluate_budget(
    *,
    organization_id: str,
    budget_digest: str,
    admission_digest: str,
    limits: Mapping[str, object],
    observed: Mapping[str, object],
    recorded_at: datetime,
    record_id: str,
) -> BudgetEvaluation:
    """Compare every projected dimension; equality remains within budget."""

    require_sha256(budget_digest, "budget_digest")
    require_sha256(admission_digest, "admission_digest")
    expected_limits = {item[0] for item in LIMIT_TO_OBSERVED}
    expected_observed = {item[1] for item in LIMIT_TO_OBSERVED}
    if set(limits) != expected_limits or set(observed) != expected_observed:
        raise BudgetValidationError("budget limits and observed dimensions must be complete and closed")
    normalized_limits: dict[str, int] = {}
    normalized_observed: dict[str, int] = {}
    exceeded: list[str] = []
    for limit_name, observed_name, dimension, limit_min, limit_max, observed_min, observed_max in LIMIT_TO_OBSERVED:
        limit = _bounded_int(limits[limit_name], limit_min, limit_max, f"limits.{limit_name}")
        current = _bounded_int(observed[observed_name], observed_min, observed_max, f"observed.{observed_name}")
        normalized_limits[limit_name] = limit
        normalized_observed[observed_name] = current
        if current > limit:
            exceeded.append(dimension)
    within = not exceeded
    document: dict[str, object] = {
        "apiVersion": "harness.planeon.ai/v1alpha1",
        "kind": "BudgetConsumption",
        "metadata": {"id": record_id, "version": "1.0.0"},
        "spec": {
            "organizationId": organization_id,
            "budgetDigest": budget_digest,
            "admissionDigest": admission_digest,
            "limits": normalized_limits,
            "observed": normalized_observed,
            "decision": "WITHIN_BUDGET" if within else "OVER_BUDGET",
            "exceededDimensions": exceeded,
            "recordedAt": _timestamp(recorded_at),
        },
    }
    return BudgetEvaluation(
        within_budget=within,
        exceeded_dimensions=tuple(exceeded),
        document=MappingProxyType(document),
        digest=document_digest(document),
    )
