from __future__ import annotations

import copy
import json
import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path
from typing import Mapping


ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "python" / "src"))

from planeon_harness.authz import AuthorizationDenied, require_admitted  # noqa: E402
from planeon_harness.runtime import ReplayReservation, verify_admission  # noqa: E402


FIXTURES = ROOT / "fixtures" / "runtime"
NOW = datetime(2030, 2, 1, 0, 0, 1, tzinfo=timezone.utc)
LIMITS = {
    "maxConcurrentTasks": 4,
    "maxTaskSeconds": 300,
    "maxRetries": 2,
    "maxToolCalls": 20,
    "maxModelTokens": 4096,
}
OBSERVED = {
    "concurrentTasks": 4,
    "taskSeconds": 300,
    "retries": 2,
    "toolCalls": 20,
    "modelTokens": 4096,
}


def load(name: str) -> dict[str, object]:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


class Store:
    def __init__(self, status: str = "RESERVED") -> None:
        self.status = status
        self.records: list[Mapping[str, object]] = []

    def reserve(self, record: Mapping[str, object]) -> ReplayReservation:
        self.records.append(record)
        if self.status == "IDEMPOTENT":
            return ReplayReservation(self.status, cached_receipt=load("valid-admission-receipt.json"))
        return ReplayReservation(self.status)

    def commit(self, record: Mapping[str, object], *, receipt_digest: str, accepted: bool) -> Mapping[str, object]:
        raise NotImplementedError


def decide(
    envelope: dict[str, object] | None = None,
    bundle: dict[str, object] | None = None,
    *,
    store: Store | None = None,
    now: datetime = NOW,
    organization_id: str = "acme.example",
    observed: Mapping[str, object] = OBSERVED,
):
    return verify_admission(
        envelope or load("valid-admission-envelope.json"),
        bundle or load("valid-trust-bundle.json"),
        expected_organization_id=organization_id,
        idempotency_key_digest="sha256:" + "6" * 64,
        limits=LIMITS,
        observed=observed,
        replay_store=store or Store(),
        now=now,
    )


class AdmissionTests(unittest.TestCase):
    def test_valid_vector_admits_and_builds_budget_and_replay_evidence(self) -> None:
        store = Store()
        result = decide(store=store)
        self.assertTrue(result.admitted)
        self.assertIsNone(result.reason_code)
        self.assertTrue(result.budget_evaluation.within_budget)
        self.assertEqual(result.replay_record["spec"]["state"], "RESERVED")
        self.assertEqual(len(store.records), 1)
        require_admitted(result)

    def test_closed_denial_precedence_vectors(self) -> None:
        cases: list[tuple[str, object, str]] = []
        malformed = load("valid-admission-envelope.json")
        malformed["payload"]["unknown"] = True
        cases.append(("malformed", malformed, "MALFORMED"))
        mismatch = load("valid-admission-envelope.json")
        mismatch["payload"]["requestDigest"] = "sha256:" + "1" * 64
        cases.append(("digest", mismatch, "DIGEST_MISMATCH"))
        forged = load("valid-admission-envelope.json")
        value = forged["signature"]["value"]
        forged["signature"]["value"] = ("A" if value[0] != "A" else "B") + value[1:]
        cases.append(("forged", forged, "SIGNATURE_INVALID"))
        unknown = load("valid-admission-envelope.json")
        unknown["signature"]["keyId"] = "test.unknown-01"
        cases.append(("unknown", unknown, "SIGNER_UNKNOWN"))
        for name, envelope, reason in cases:
            with self.subTest(name=name):
                self.assertEqual(decide(envelope=envelope).reason_code, reason)

    def test_key_state_purpose_tenant_and_time_fail_closed(self) -> None:
        mutations = []
        pending = load("valid-trust-bundle.json")
        pending["payload"]["keys"][0]["state"] = "PENDING"
        mutations.append((pending, "SIGNER_NOT_ACTIVE"))
        revoked = load("valid-trust-bundle.json")
        revoked["payload"]["keys"][0].update(
            state="REVOKED",
            revokedAt="2030-01-15T00:00:00Z",
            revocationReason="KEY_COMPROMISE",
        )
        mutations.append((revoked, "SIGNER_REVOKED"))
        wrong_purpose = load("valid-trust-bundle.json")
        wrong_purpose["payload"]["keys"][0]["purposes"] = ["RUNTIME_RECEIPT"]
        mutations.append((wrong_purpose, "KEY_PURPOSE_MISMATCH"))
        for bundle, reason in mutations:
            with self.subTest(reason=reason):
                self.assertEqual(decide(bundle=bundle).reason_code, reason)
        self.assertEqual(decide(organization_id="other.example").reason_code, "TENANT_MISMATCH")
        self.assertEqual(
            decide(now=datetime(2030, 1, 31, 23, 59, 59, tzinfo=timezone.utc)).reason_code,
            "ENVELOPE_NOT_YET_VALID",
        )
        self.assertEqual(
            decide(now=datetime(2030, 2, 1, 0, 5, 0, tzinfo=timezone.utc)).reason_code,
            "ENVELOPE_EXPIRED",
        )

    def test_replay_idempotency_and_budget_outcomes_are_distinct(self) -> None:
        self.assertEqual(decide(store=Store("REPLAY_DETECTED")).reason_code, "REPLAY_DETECTED")
        self.assertEqual(
            decide(store=Store("IDEMPOTENCY_CONFLICT")).reason_code,
            "IDEMPOTENCY_CONFLICT",
        )
        idempotent = decide(store=Store("IDEMPOTENT"))
        self.assertTrue(idempotent.admitted)
        self.assertIsNotNone(idempotent.cached_receipt)
        over = dict(OBSERVED)
        over["modelTokens"] = 4097
        result = decide(observed=over)
        self.assertEqual(result.reason_code, "BUDGET_EXCEEDED")
        self.assertEqual(result.budget_evaluation.exceeded_dimensions, ("MODEL_TOKENS",))

    def test_authorization_helper_never_accepts_a_denial(self) -> None:
        denied = decide(store=Store("REPLAY_DETECTED"))
        with self.assertRaisesRegex(AuthorizationDenied, "REPLAY_DETECTED"):
            require_admitted(denied)


if __name__ == "__main__":
    unittest.main()
