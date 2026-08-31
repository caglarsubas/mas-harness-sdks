from __future__ import annotations

import base64
import copy
import json
import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "python" / "src"))

from planeon_harness.runtime import (  # noqa: E402
    canonical_json,
    document_digest,
    parse_json_strict,
    sha256_digest,
    signed_message,
    verify_bootstrap_bundle,
    verify_receipt,
    verify_rotated_bundle,
)
from planeon_harness.runtime.crypto import verify_document_signature  # noqa: E402


FIXTURES = ROOT / "fixtures" / "runtime"


def load(name: str) -> dict[str, object]:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


class RuntimeVectorTests(unittest.TestCase):
    def test_signed_documents_match_every_public_golden_byte_and_signature(self) -> None:
        vectors = load("interoperability-vectors.json")
        public_key = vectors["publicKey"]
        self.assertTrue(vectors["testOnly"])
        for vector in vectors["signedDocuments"]:
            with self.subTest(kind=vector["kind"]):
                document = load(vector["fixture"])
                message = signed_message(document["kind"], document["payload"])
                canonical_payload = base64.urlsafe_b64decode(
                    vector["canonicalPayloadBase64url"] + "=="
                )
                self.assertEqual(canonical_json(document["payload"]), canonical_payload)
                self.assertEqual(sha256_digest(message), vector["signedMessageDigest"])
                self.assertEqual(document["signature"]["value"], vector["signature"])
                self.assertEqual(verify_document_signature(document, public_key), (True, True))

    def test_bootstrap_and_receipt_verification_use_exact_key_and_time(self) -> None:
        bundle = load("valid-trust-bundle.json")
        now = datetime(2030, 2, 1, 0, 0, 1, tzinfo=timezone.utc)
        result = verify_bootstrap_bundle(
            bundle,
            pinned_digest=document_digest(bundle),
            expected_organization_id="acme.example",
            now=now,
        )
        self.assertTrue(result.accepted)
        receipt = verify_receipt(
            load("valid-admission-receipt.json"),
            bundle,
            expected_organization_id="acme.example",
            now=now,
        )
        self.assertTrue(receipt.accepted)

    def test_strict_parser_rejects_duplicate_floats_and_non_ascii(self) -> None:
        for raw in ('{"a":1,"a":2}', '{"a":1.5}', '{"a":"é"}'):
            with self.subTest(raw=raw), self.assertRaises(ValueError):
                canonical_json(parse_json_strict(raw))

    def test_rotation_is_bound_to_exact_predecessor_digest(self) -> None:
        predecessor = load("valid-trust-bundle.json")
        candidate = copy.deepcopy(predecessor)
        candidate["payload"]["bundleVersion"] = 2
        candidate["payload"]["previousBundleDigest"] = "sha256:" + "0" * 64
        result = verify_rotated_bundle(
            candidate,
            predecessor,
            expected_organization_id="acme.example",
            now=datetime(2030, 2, 1, 0, 0, 1, tzinfo=timezone.utc),
        )
        self.assertEqual(result.reason_code, "DIGEST_MISMATCH")

    def test_forged_signature_is_not_treated_as_digest_mismatch(self) -> None:
        document = load("valid-admission-envelope.json")
        forged = copy.deepcopy(document)
        value = forged["signature"]["value"]
        forged["signature"]["value"] = ("A" if value[0] != "A" else "B") + value[1:]
        self.assertEqual(
            verify_document_signature(forged, load("interoperability-vectors.json")["publicKey"]),
            (True, False),
        )


if __name__ == "__main__":
    unittest.main()
