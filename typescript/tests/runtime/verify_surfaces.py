from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]


def main() -> int:
    package = json.loads((ROOT / "typescript" / "package.json").read_text())
    runtime = package["exports"]["./runtime"]
    assert runtime == {
        "types": "./dist/runtime/index.d.ts",
        "import": "./dist/runtime/index.js",
    }
    source = (ROOT / "typescript" / "src" / "runtime" / "index.ts").read_text()
    distribution = (ROOT / "typescript" / "dist" / "runtime" / "index.js").read_text()
    declaration = (ROOT / "typescript" / "dist" / "runtime" / "index.d.ts").read_text()
    for value in (source, distribution):
        assert "fetch(" not in value
        assert "privateKey" not in value
        assert "subtle.verify" in value
    assert "verifyAdmission" in declaration
    assert "verifyRotatedBundle" in declaration
    assert "AtomicReplayStore" in declaration
    print("TypeScript runtime source, dist, declarations, and export map are synchronized")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
