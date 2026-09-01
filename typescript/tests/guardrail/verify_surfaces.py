from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
SOURCE_INDEX = ROOT / "typescript" / "src" / "guardrail" / "index.ts"
SOURCE_RUNTIME = ROOT / "typescript" / "src" / "guardrail" / "runtime.js"
DIST = ROOT / "typescript" / "dist" / "guardrail" / "index.js"
DECLARATIONS = ROOT / "typescript" / "dist" / "guardrail" / "index.d.ts"
PACKAGE = ROOT / "typescript" / "package.json"


def main() -> None:
    source_index = SOURCE_INDEX.read_text(encoding="utf-8")
    source_runtime = SOURCE_RUNTIME.read_text(encoding="utf-8")
    distribution = DIST.read_text(encoding="utf-8")
    declarations = DECLARATIONS.read_text(encoding="utf-8")
    package = json.loads(PACKAGE.read_text(encoding="utf-8"))

    assert SOURCE_RUNTIME.read_bytes() == DIST.read_bytes()
    public_names = {
        "GuardrailClient",
        "GuardrailStream",
        "GuardrailDetector",
        "GuardrailProfile",
        "GuardrailRequest",
        "DetectorFinding",
        "RedactionRange",
        "GuardrailResult",
        "GuardrailContractError",
        "canonicalGuardrailResult",
    }
    for name in public_names:
        assert name in source_index, name
        assert name in declarations, name
    for name in {
        "GuardrailClient",
        "GuardrailStream",
        "GuardrailContractError",
        "canonicalGuardrailResult",
    }:
        assert name in source_runtime, name
        assert name in distribution, name

    assert package["dependencies"] == {}
    assert package["exports"]["./guardrail"] == {
        "types": "./dist/guardrail/index.d.ts",
        "import": "./dist/guardrail/index.js",
    }
    combined = (source_runtime + distribution).casefold()
    for forbidden in (
        "fetch(",
        "websocket",
        "http://",
        "https://",
        "process.env",
        "console.",
        "api_key",
        "apikey",
        "credential",
        "exporter",
        "moderation",
    ):
        assert forbidden not in combined, forbidden
    print("TypeScript guardrail source, distribution, declarations, and exports are synchronized")


if __name__ == "__main__":
    main()
