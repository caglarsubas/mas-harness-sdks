from __future__ import annotations

import hashlib
import json
import re
import unittest
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
SHA256 = re.compile(r"^sha256:[0-9a-f]{64}$")
GIT_OBJECT = re.compile(r"^[0-9a-f]{40}$")


class EvidenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.evidence = json.loads(
            (REPOSITORY_ROOT / "examples" / "telemetry" / "clean-room-evidence.json").read_text(
                encoding="utf-8"
            )
        )

    def test_clean_room_and_copy_boundaries_are_closed(self) -> None:
        implementation = self.evidence["implementation"]
        self.assertFalse(implementation["sourceBytesObserved"])
        self.assertFalse(implementation["sourceCheckoutMounted"])
        self.assertFalse(implementation["sourceCodeCopiedAdaptedTranslatedOrExecuted"])
        self.assertFalse(self.evidence["provenanceAuthority"]["copyAuthorizationEnabled"])
        self.assertEqual(self.evidence["porting"]["authorizationCount"], 0)
        self.assertFalse(self.evidence["porting"]["destinationLedgerModified"])

    def test_public_authority_hashes_and_git_objects_are_pinned(self) -> None:
        packet_authority = self.evidence["packetAuthority"]
        self.assertRegex(packet_authority["packetSha256"], SHA256)
        self.assertRegex(packet_authority["commit"], GIT_OBJECT)
        authority = self.evidence["provenanceAuthority"]
        self.assertRegex(authority["indexSha256"], SHA256)
        self.assertRegex(authority["commit"], GIT_OBJECT)
        self.assertRegex(authority["sourceCommit"], GIT_OBJECT)
        paths = []
        for reference in authority["sourceReferences"]:
            self.assertRegex(reference["gitObject"], GIT_OBJECT)
            self.assertEqual(reference["reuseDisposition"], "REFERENCE_ONLY_PENDING_PATH_REVIEW")
            paths.append(reference["path"])
        self.assertEqual(paths, sorted(paths))

    def test_destination_porting_ledger_is_byte_unchanged(self) -> None:
        digest = hashlib.sha256((REPOSITORY_ROOT / "PORTING.yaml").read_bytes()).hexdigest()
        self.assertEqual(
            self.evidence["porting"]["destinationLedgerSha256"],
            f"sha256:{digest}",
        )

    def test_behavioral_change_and_vector_records_are_complete(self) -> None:
        ids = [item["id"] for item in self.evidence["behavioralChanges"]]
        self.assertEqual(ids, sorted(ids))
        self.assertEqual(len(ids), len(set(ids)))
        vectors = json.loads(
            (REPOSITORY_ROOT / "examples" / "telemetry" / "golden-span-vectors.json").read_text(
                encoding="utf-8"
            )
        )
        expected_ids = sorted(item["id"] for item in vectors["vectors"])
        self.assertEqual(
            self.evidence["verification"]["crossLanguageGoldenVectorIds"],
            expected_ids,
        )


if __name__ == "__main__":
    unittest.main()
