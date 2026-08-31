# Optional integration adapters

SDK-005 adds Python invocation adapters without changing the base dependency
set. Install only the framework used by the tenant's offline dependency mirror:

| Extra | Bounded surface |
|---|---|
| `planeon-harness-sdk[langchain]` | runnable `invoke` and `ainvoke` |
| `planeon-harness-sdk[langgraph]` | graph `invoke` and `ainvoke` |
| `planeon-harness-sdk[crewai]` | crew `kickoff` and `kickoff_async` |
| `planeon-harness-sdk[semantic-kernel]` | kernel `invoke` and `invoke_prompt` |
| `planeon-harness-sdk[mcp]` | client `call_tool` |

Importing `planeon_harness` or `planeon_harness.integrations` does not import
any framework. Import the required factory from its framework module and wrap an
already-constructed local object. Construction performs no call, registration,
endpoint lookup, credential lookup, or network operation.

```python
from planeon_harness.decorators import InMemorySpanSink
from planeon_harness.integrations.langgraph import instrument_langgraph

sink = InMemorySpanSink()
graph = build_your_local_graph()
instrumented = instrument_langgraph(graph, sink=sink)
result = instrumented.invoke({"request": "tenant-owned input"})
```

Arguments, prompts, messages, results, exception text, and framework state are
not recorded. The adapter emits fixed `harness.integration.*` operation names
only to the caller-supplied sink. No sink means the local no-op sink.

Vector search is deliberately vendor-neutral and requires no extra. See
`vector_local.py` for an offline example. Compatibility baselines live in
`python/optional-dependencies.lock`; their verification state is
`OFFLINE_FAKE_SURFACE_ONLY`, not live upstream-package certification.
