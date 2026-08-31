"""Closed HarnessCloudEvent v1alpha1 validation and serialization."""

from __future__ import annotations

import re
from collections.abc import Mapping
from datetime import datetime
from typing import Any

from ._json import MAX_SAFE_INTEGER, detached_json, deterministic_json_bytes
from .errors import ProtocolHelperError


_TOP_FIELDS = {
    "data", "datacontenttype", "dataschema", "id", "organizationid", "partitionkey",
    "sequence", "source", "specversion", "subject", "time", "type",
}
_DATA_FIELDS = {
    "schemaVersion", "aggregateKind", "aggregateId", "aggregateVersion", "actor",
    "correlationId", "causationId", "reasonCode", "transition", "resourceRefs", "evidenceRefs",
}
_EVENT_TYPES = {
    "harness.approval.state.changed.v1": ("ApprovalRequest", False),
    "harness.bundle-release.state.changed.v1": ("BundleRelease", False),
    "harness.evidence.state.changed.v1": ("EvidenceRecord", False),
    "harness.installation.state.changed.v1": ("HarnessInstallation", False),
    "harness.operation.state.changed.v1": ("Operation", False),
    "harness.policy-bundle.state.changed.v1": ("PolicyBundle", False),
    "harness.status.projection.updated.v1": (
        {"TenantHarnessOverview", "PlaneStatusProjection", "HarnessStatusProjection"}, True
    ),
}
_STABLE_ID = re.compile(r"^[a-z][a-z0-9]*(?:[.-][a-z0-9]+)+$")
_STATE = re.compile(r"^[A-Z][A-Z0-9]*(?:_[A-Z0-9]+)*$")
_UUID4 = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$")
_DIGEST = re.compile(r"^sha256:[0-9a-f]{64}$")
_SOURCE = re.compile(r"^urn:planeon:harness:[a-z][a-z0-9]*(?:[.-][a-z0-9]+)+$")
_TIMESTAMP = re.compile(r"^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z$")


def _fail(message: str) -> None:
    raise ProtocolHelperError("MALFORMED_CLOUD_EVENT", message)


def _closed(value: object, fields: set[str], context: str) -> dict[str, Any]:
    if not isinstance(value, Mapping) or not all(isinstance(key, str) for key in value):
        _fail(f"{context} must be an object")
    result = dict(value)
    if set(result) != fields:
        _fail(f"{context} fields are closed")
    return result


def _match(value: object, pattern: re.Pattern[str], context: str) -> str:
    if not isinstance(value, str) or pattern.fullmatch(value) is None:
        _fail(f"{context} is invalid")
    return value


def _stable_id(value: object, context: str) -> str:
    result = _match(value, _STABLE_ID, context)
    if len(result) > 128:
        _fail(f"{context} exceeds the stable identifier limit")
    return result


def _timestamp(value: object, context: str) -> None:
    text = _match(value, _TIMESTAMP, context)
    try:
        datetime.strptime(text, "%Y-%m-%dT%H:%M:%SZ")
    except ValueError:
        _fail(f"{context} is not a calendar timestamp")


def _references(value: object, context: str) -> None:
    if not isinstance(value, list):
        _fail(f"{context} must be an array")
    seen: set[bytes] = set()
    for index, item in enumerate(value):
        reference = _closed(item, {"kind", "id", "digest"}, f"{context}[{index}]")
        _stable_id(reference["kind"], f"{context}[{index}].kind")
        _stable_id(reference["id"], f"{context}[{index}].id")
        _match(reference["digest"], _DIGEST, f"{context}[{index}].digest")
        encoded = deterministic_json_bytes(reference)
        if encoded in seen:
            _fail(f"{context} contains duplicate references")
        seen.add(encoded)


def validate_harness_cloud_event(value: object) -> dict[str, Any]:
    """Validate the exact pinned HarnessCloudEvent schema without extensions."""

    event = _closed(value, _TOP_FIELDS, "HarnessCloudEvent")
    if event["specversion"] != "1.0" or event["datacontenttype"] != "application/json":
        _fail("CloudEvents version or content type is invalid")
    if event["dataschema"] != "https://harness.planeon.ai/schemas/v1alpha1/events/harness-cloud-event.schema.json":
        _fail("dataschema is not the pinned HarnessCloudEvent contract")
    _match(event["id"], _UUID4, "id")
    _match(event["source"], _SOURCE, "source")
    _stable_id(event["subject"], "subject")
    _stable_id(event["organizationid"], "organizationid")
    _stable_id(event["partitionkey"], "partitionkey")
    _timestamp(event["time"], "time")
    sequence = event["sequence"]
    if isinstance(sequence, bool) or not isinstance(sequence, int) or not 1 <= sequence <= MAX_SAFE_INTEGER:
        _fail("sequence must be a positive safe integer")
    if event["type"] not in _EVENT_TYPES:
        _fail("event type is not admitted")

    data = _closed(event["data"], _DATA_FIELDS, "data")
    if data["schemaVersion"] != "harness.planeon.ai/event-data/v1alpha1":
        _fail("data.schemaVersion is invalid")
    _stable_id(data["aggregateId"], "data.aggregateId")
    aggregate_version = data["aggregateVersion"]
    if isinstance(aggregate_version, bool) or not isinstance(aggregate_version, int) or not 1 <= aggregate_version <= MAX_SAFE_INTEGER:
        _fail("data.aggregateVersion must be a positive safe integer")
    actor = _closed(data["actor"], {"type", "id"}, "data.actor")
    if actor["type"] not in {"HUMAN", "WORKLOAD", "SYSTEM", "TENANT"}:
        _fail("data.actor.type is invalid")
    _stable_id(actor["id"], "data.actor.id")
    _match(data["correlationId"], _UUID4, "data.correlationId")
    if data["causationId"] is not None:
        _match(data["causationId"], _UUID4, "data.causationId")
    _match(data["reasonCode"], _STATE, "data.reasonCode")
    transition = data["transition"]
    if transition is not None:
        transition = _closed(transition, {"from", "to"}, "data.transition")
        _match(transition["from"], _STATE, "data.transition.from")
        _match(transition["to"], _STATE, "data.transition.to")
    _references(data["resourceRefs"], "data.resourceRefs")
    _references(data["evidenceRefs"], "data.evidenceRefs")

    aggregate_requirement, transition_must_be_null = _EVENT_TYPES[event["type"]]
    if isinstance(aggregate_requirement, set):
        if data["aggregateKind"] not in aggregate_requirement:
            _fail("event type and aggregate kind differ")
    elif data["aggregateKind"] != aggregate_requirement:
        _fail("event type and aggregate kind differ")
    if transition_must_be_null and data["transition"] is not None:
        _fail("status projection events cannot carry a transition")
    if not transition_must_be_null and not isinstance(data["transition"], Mapping):
        _fail("state-change events require a transition")
    return detached_json(event)


def serialize_harness_cloud_event(value: object) -> bytes:
    """Return deterministic UTF-8 structured-mode JSON for one valid event."""

    return deterministic_json_bytes(validate_harness_cloud_event(value))
