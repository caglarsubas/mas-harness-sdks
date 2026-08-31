"""Provider-neutral, offline vector adapter example."""

from __future__ import annotations

import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "python" / "src"))

from planeon_harness.decorators import InMemorySpanSink  # noqa: E402
from planeon_harness.integrations import instrument_vector_search  # noqa: E402


def local_search(_query: tuple[float, ...]) -> tuple[str, ...]:
    return ("document-local-1", "document-local-2")


sink = InMemorySpanSink()
search = instrument_vector_search(local_search, sink=sink)
result = search((0.1, 0.2, 0.3))

assert result == ("document-local-1", "document-local-2")
assert len(sink.records) == 1
print(
    json.dumps(
        {
            "networkRequired": False,
            "operation": sink.records[0].name,
            "records": len(sink.records),
        },
        sort_keys=True,
        separators=(",", ":"),
    )
)
