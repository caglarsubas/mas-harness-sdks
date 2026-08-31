"""Local-only SDK-002 example with an explicit in-memory sink."""

from planeon_harness.context import HarnessContext, use_context
from planeon_harness.decorators import InMemorySpanSink, instrument


sink = InMemorySpanSink()
context = HarnessContext.create(
    tenant_id="tenant-example",
    organization_id="organization-example",
    harness_id="knowledge.domain-semantic",
    plane_id="knowledge",
)


@instrument(
    "harness.example.inspect",
    attributes={"harness.label.scenario": "local_only"},
    sink=sink,
)
def inspect_local_fixture() -> str:
    return "accepted"


with use_context(context):
    inspect_local_fixture()

assert len(sink.records) == 1
