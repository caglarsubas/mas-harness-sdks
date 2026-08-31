from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
SOURCE = ROOT / "typescript" / "src" / "protocols" / "index.ts"
DIST = ROOT / "typescript" / "dist" / "protocols" / "index.js"
DECLARATIONS = ROOT / "typescript" / "dist" / "protocols" / "index.d.ts"
PACKAGE = ROOT / "typescript" / "package.json"


def main() -> None:
    source = SOURCE.read_text(encoding="utf-8")
    dist = DIST.read_text(encoding="utf-8")
    declarations = DECLARATIONS.read_text(encoding="utf-8")
    package = json.loads(PACKAGE.read_text(encoding="utf-8"))
    expected = {
        "buildMcpRequest", "negotiateMcpVersion", "classifyMcpTaskState",
        "classifyA2aTaskState", "buildSseResumeHeaders", "validateHarnessCloudEvent",
        "serializeHarnessCloudEvent", "ProtocolHelperError",
    }
    for name in expected:
        assert name in source, name
        assert name in dist, name
        assert name in declarations, name
    assert package["exports"]["./protocols"] == {
        "types": "./dist/protocols/index.d.ts",
        "import": "./dist/protocols/index.js",
    }
    for value in (source, dist):
        assert "fetch(" not in value
        assert "Mcp-Authorization" not in value
        assert "privateKey" not in value
        assert "Mcp-Session-Id" in value
        assert "2026-07-28" in value and "2025-11-25" in value
    print("TypeScript protocol source, distribution, declarations, and export are synchronized")


if __name__ == "__main__":
    main()
