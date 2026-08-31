#!/usr/bin/env python3
"""Validate the dependency-free TypeScript telemetry source contract offline."""

from __future__ import annotations

import ast
import hashlib
import json
import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
SOURCE_ROOT = ROOT / "typescript" / "src" / "telemetry"
DIST_ROOT = ROOT / "typescript" / "dist" / "telemetry"
TEST_ROOT = ROOT / "typescript" / "tests" / "telemetry"
EXAMPLES = ROOT / "examples" / "telemetry"
PACKAGE_MANIFEST = ROOT / "typescript" / "package.json"

REQUIRED_SOURCE = {
    "attributes.ts": (
        "export function sanitizeAttributes",
        "export function contextAttributes",
    ),
    "canonical.ts": ("export function canonicalJson",),
    "context.ts": (
        "export function createContext",
        "export function injectContext",
        "export function extractContext",
    ),
    "decorators.ts": (
        "export function instrumentSync",
        "export function instrumentAsync",
    ),
    "index.ts": ("export * from",),
}
FORBIDDEN_SOURCE_TOKENS = (
    "fetch(",
    "xmlhttprequest",
    "websocket",
    "process.env",
    "otel_exporter",
    "node:http",
    "node:https",
    "axios",
    "openrouter",
    "declarai",
    "anthropic",
    "openai",
)
REQUIRED_DIST = {
    "index.js": (
        "export function createContext",
        "export function sanitizeAttributes",
        "export function instrumentSync",
        "export function instrumentAsync",
    ),
    "index.d.ts": (
        "export interface HarnessContext",
        "export interface SpanRecord",
        "export declare function instrumentSync",
        "export declare function instrumentAsync",
    ),
}
EXPECTED_EXPORT = {
    "types": "./dist/telemetry/index.d.ts",
    "import": "./dist/telemetry/index.js",
}


def _regular(path: Path) -> str:
    if not path.is_file() or path.is_symlink():
        raise ValueError(f"required TypeScript telemetry file is absent or linked: {path.relative_to(ROOT)}")
    return path.read_text(encoding="utf-8")


def _source_digest(files: list[Path]) -> str:
    digest = hashlib.sha256()
    for path in files:
        relative = path.relative_to(ROOT).as_posix().encode("utf-8")
        data = path.read_bytes()
        digest.update(len(relative).to_bytes(4, "big"))
        digest.update(relative)
        digest.update(len(data).to_bytes(8, "big"))
        digest.update(data)
    return f"sha256:{digest.hexdigest()}"


def verify() -> dict[str, object]:
    source_files = sorted(SOURCE_ROOT.glob("*.ts"), key=lambda item: item.name)
    if {path.name for path in source_files} != set(REQUIRED_SOURCE):
        raise ValueError("TypeScript telemetry source file set is not closed")
    combined = ""
    for path in source_files:
        text = _regular(path)
        combined += text
        for required in REQUIRED_SOURCE[path.name]:
            if required not in text:
                raise ValueError(f"missing required export in {path.relative_to(ROOT)}: {required}")
        for specifier in re.findall(r'from\s+"([^"]+)"', text):
            if not specifier.startswith("./"):
                raise ValueError(f"core TypeScript source imports a non-relative module: {specifier}")
    folded = combined.casefold().replace(" ", "")
    for token in FORBIDDEN_SOURCE_TOKENS:
        if token in folded:
            raise ValueError(f"TypeScript telemetry source contains forbidden token: {token}")
    decorators = _regular(SOURCE_ROOT / "decorators.ts")
    if ".message" in decorators or ".stack" in decorators or "...args" not in decorators:
        raise ValueError("decorator capture boundary differs from SDK-002 authority")
    if "NULL_SINK" not in decorators or "strictSink" not in decorators:
        raise ValueError("no-op sink and explicit strict mode are required")
    if "redactedKeys" in combined:
        raise ValueError("rejected telemetry key names must not be retained")

    attributes = _regular(SOURCE_ROOT / "attributes.ts")
    match = re.search(r"SEMANTIC_ATTRIBUTE_KEYS_JSON = ('(?:[^'\\]|\\.)*') as const;", attributes)
    if match is None:
        raise ValueError("TypeScript semantic attribute JSON literal is absent")
    key_json = ast.literal_eval(match.group(1))
    key_contract = json.loads(_regular(EXAMPLES / "attribute-contract.json"))["keys"]
    if json.loads(key_json) != key_contract:
        raise ValueError("TypeScript semantic attributes differ from the shared contract")

    dist_files = sorted(DIST_ROOT.iterdir(), key=lambda item: item.name)
    if {path.name for path in dist_files if path.is_file()} != set(REQUIRED_DIST):
        raise ValueError("TypeScript telemetry distribution file set is not closed")
    dist_text: dict[str, str] = {}
    for path in dist_files:
        if path.name not in REQUIRED_DIST:
            raise ValueError(f"undeclared TypeScript telemetry distribution entry: {path.name}")
        text = _regular(path)
        dist_text[path.name] = text
        for required in REQUIRED_DIST[path.name]:
            if required not in text:
                raise ValueError(f"missing required distribution surface: {required}")
    folded_dist = dist_text["index.js"].casefold().replace(" ", "")
    if "redactedKeys" in dist_text["index.js"] or "redactedKeys" in dist_text["index.d.ts"]:
        raise ValueError("distribution must not retain rejected telemetry key names")
    for token in FORBIDDEN_SOURCE_TOKENS:
        if token in folded_dist:
            raise ValueError(f"TypeScript telemetry distribution contains forbidden token: {token}")
    dist_match = re.search(
        r"SEMANTIC_ATTRIBUTE_KEYS_JSON = ('(?:[^'\\]|\\.)*');",
        dist_text["index.js"],
    )
    if dist_match is None or json.loads(ast.literal_eval(dist_match.group(1))) != key_contract:
        raise ValueError("TypeScript distribution semantic attributes differ from the contract")

    manifest = json.loads(_regular(PACKAGE_MANIFEST))
    if manifest.get("exports", {}).get("./telemetry") != EXPECTED_EXPORT:
        raise ValueError("package telemetry export differs from SDK-002 authority")
    if manifest.get("dependencies") != {} or manifest.get("devDependencies") != {}:
        raise ValueError("TypeScript telemetry package must remain dependency-free")

    vector_document = json.loads(_regular(EXAMPLES / "golden-span-vectors.json"))
    vector_ids = sorted(vector["id"] for vector in vector_document["vectors"])
    test_text = _regular(TEST_ROOT / "telemetry.test.ts")
    package_test_text = _regular(TEST_ROOT / "package-runtime.test.mjs")
    for vector_id in vector_ids:
        if test_text.count(f'"{vector_id}"') != 1:
            raise ValueError(f"TypeScript test does not pin vector exactly once: {vector_id}")
        if package_test_text.count(f'"{vector_id}"') != 1:
            raise ValueError(f"package runtime test does not pin vector exactly once: {vector_id}")
    example = _regular(EXAMPLES / "typescript_example.ts")
    for required in ("createContext", "instrumentSync", "harness.label.scenario"):
        if required not in example:
            raise ValueError(f"TypeScript example is missing required behavior: {required}")
    return {
        "accepted": True,
        "dependencies": 0,
        "externalExporter": False,
        "rawContentCapture": False,
        "sourceDigest": _source_digest(
            source_files
            + dist_files
            + [
                PACKAGE_MANIFEST,
                TEST_ROOT / "telemetry.test.ts",
                TEST_ROOT / "package-runtime.test.mjs",
                EXAMPLES / "typescript_example.ts",
            ]
        ),
        "distributionFiles": len(dist_files),
        "packageExport": "./telemetry",
        "sourceFiles": len(source_files),
        "vectorIds": vector_ids,
    }


def main() -> int:
    try:
        report = verify()
    except (OSError, UnicodeError, ValueError, json.JSONDecodeError, SyntaxError) as exc:
        print(f"TypeScript telemetry verification refused: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(report, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
