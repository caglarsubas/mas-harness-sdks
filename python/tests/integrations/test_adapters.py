from __future__ import annotations

import asyncio
import json
import sys
import unittest
from pathlib import Path
from types import ModuleType
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "python" / "src"))

from planeon_harness.decorators import InMemorySpanSink  # noqa: E402
from planeon_harness.integrations import IntegrationContractError  # noqa: E402
from planeon_harness.integrations.crewai import instrument_crewai  # noqa: E402
from planeon_harness.integrations.langchain import instrument_langchain_runnable  # noqa: E402
from planeon_harness.integrations.langgraph import instrument_langgraph  # noqa: E402
from planeon_harness.integrations.mcp import instrument_mcp_client  # noqa: E402
from planeon_harness.integrations.semantic_kernel import (  # noqa: E402
    instrument_semantic_kernel,
)
from planeon_harness.protocols import MCP_COMPATIBILITY, MCP_CURRENT, ProtocolHelperError  # noqa: E402


class DualInvocationFake:
    def __init__(self) -> None:
        self.calls: list[tuple[str, tuple[object, ...], dict[str, object]]] = []

    def invoke(self, *args, **kwargs):
        self.calls.append(("invoke", args, kwargs))
        return "sync-result"

    async def ainvoke(self, *args, **kwargs):
        self.calls.append(("ainvoke", args, kwargs))
        return "async-result"


class CrewFake:
    def __init__(self) -> None:
        self.calls: list[str] = []

    def kickoff(self, *args, **kwargs):
        del args, kwargs
        self.calls.append("kickoff")
        return "crew-result"

    async def kickoff_async(self, *args, **kwargs):
        del args, kwargs
        self.calls.append("kickoff_async")
        return "crew-async-result"


class KernelFake:
    def __init__(self) -> None:
        self.calls: list[str] = []

    async def invoke(self, *args, **kwargs):
        del args, kwargs
        self.calls.append("invoke")
        return "kernel-result"

    async def invoke_prompt(self, *args, **kwargs):
        del args, kwargs
        self.calls.append("invoke_prompt")
        return "prompt-result"


class MCPFake:
    def __init__(self) -> None:
        self.calls: list[tuple[object, object, dict[str, object]]] = []

    async def call_tool(self, name, arguments, **kwargs):
        self.calls.append((name, arguments, kwargs))
        return "tool-result"


class FrameworkFailure(RuntimeError):
    pass


class FailureDual:
    def __init__(self, failure: FrameworkFailure) -> None:
        self.failure = failure

    def invoke(self, *args, **kwargs):
        del args, kwargs
        raise self.failure

    async def ainvoke(self, *args, **kwargs):
        del args, kwargs
        raise self.failure


class FailureCrew:
    def __init__(self, failure: FrameworkFailure) -> None:
        self.failure = failure

    def kickoff(self, *args, **kwargs):
        del args, kwargs
        raise self.failure

    async def kickoff_async(self, *args, **kwargs):
        del args, kwargs
        raise self.failure


class FailureKernel:
    def __init__(self, failure: FrameworkFailure) -> None:
        self.failure = failure

    async def invoke(self, *args, **kwargs):
        del args, kwargs
        raise self.failure

    async def invoke_prompt(self, *args, **kwargs):
        del args, kwargs
        raise self.failure


class FailureMCP:
    def __init__(self, failure: FrameworkFailure) -> None:
        self.failure = failure

    async def call_tool(self, *args, **kwargs):
        del args, kwargs
        raise self.failure


class AdapterTests(unittest.TestCase):
    def fake_module(self, import_name: str):
        return patch.dict(sys.modules, {import_name: ModuleType(import_name)})

    def test_langchain_and_langgraph_delegate_only_when_invoked(self) -> None:
        cases = (
            ("langchain_core", instrument_langchain_runnable, "langchain"),
            ("langgraph", instrument_langgraph, "langgraph"),
        )
        for import_name, factory, operation_prefix in cases:
            with self.subTest(import_name=import_name), self.fake_module(import_name):
                target = DualInvocationFake()
                sink = InMemorySpanSink()
                adapter = factory(target, sink=sink)
                self.assertEqual(target.calls, [])
                self.assertEqual(adapter.invoke("PRIVATE_ARGUMENT"), "sync-result")
                self.assertEqual(asyncio.run(adapter.ainvoke("PRIVATE_ARGUMENT")), "async-result")
                self.assertEqual([call[0] for call in target.calls], ["invoke", "ainvoke"])
                self.assertEqual(
                    [record.name for record in sink.records],
                    [
                        f"harness.integration.{operation_prefix}.invoke",
                        f"harness.integration.{operation_prefix}.ainvoke",
                    ],
                )
                self.assertNotIn(
                    "PRIVATE_ARGUMENT",
                    json.dumps([record.to_dict() for record in sink.records], sort_keys=True),
                )

    def test_crewai_delegate_is_bounded_to_kickoff_methods(self) -> None:
        with self.fake_module("crewai"):
            target = CrewFake()
            sink = InMemorySpanSink()
            adapter = instrument_crewai(target, sink=sink)
            self.assertEqual(target.calls, [])
            self.assertEqual(adapter.kickoff(inputs={"topic": "PRIVATE"}), "crew-result")
            self.assertEqual(asyncio.run(adapter.kickoff_async()), "crew-async-result")
            self.assertEqual(target.calls, ["kickoff", "kickoff_async"])
            self.assertEqual(
                [record.name for record in sink.records],
                [
                    "harness.integration.crewai.kickoff",
                    "harness.integration.crewai.kickoff_async",
                ],
            )
            self.assertNotIn(
                "PRIVATE",
                json.dumps([record.to_dict() for record in sink.records], sort_keys=True),
            )

    def test_semantic_kernel_delegate_is_async_and_bounded(self) -> None:
        with self.fake_module("semantic_kernel"):
            target = KernelFake()
            sink = InMemorySpanSink()
            adapter = instrument_semantic_kernel(target, sink=sink)
            self.assertEqual(target.calls, [])
            self.assertEqual(asyncio.run(adapter.invoke("PRIVATE")), "kernel-result")
            self.assertEqual(asyncio.run(adapter.invoke_prompt("PRIVATE")), "prompt-result")
            self.assertEqual(target.calls, ["invoke", "invoke_prompt"])
            self.assertEqual(
                [record.name for record in sink.records],
                [
                    "harness.integration.semantic_kernel.invoke",
                    "harness.integration.semantic_kernel.invoke_prompt",
                ],
            )
            self.assertNotIn(
                "PRIVATE",
                json.dumps([record.to_dict() for record in sink.records], sort_keys=True),
            )

    def test_mcp_delegate_accepts_only_sdk004_revisions(self) -> None:
        with self.fake_module("mcp"):
            for version in (MCP_CURRENT, MCP_COMPATIBILITY):
                with self.subTest(version=version):
                    target = MCPFake()
                    sink = InMemorySpanSink()
                    adapter = instrument_mcp_client(
                        target,
                        protocol_version=version,
                        sink=sink,
                    )
                    self.assertEqual(target.calls, [])
                    self.assertEqual(
                        asyncio.run(adapter.call_tool("local_search", {"query": "PRIVATE"})),
                        "tool-result",
                    )
                    self.assertEqual(adapter.protocol_version, version)
                    self.assertEqual(target.calls[0][0], "local_search")
                    self.assertEqual(sink.records[0].name, "harness.integration.mcp.call_tool")
                    self.assertNotIn("PRIVATE", sink.records[0].canonical_json())
            with self.assertRaises(ProtocolHelperError) as caught:
                instrument_mcp_client(MCPFake(), protocol_version="2025-06-18")
            self.assertEqual(caught.exception.code, "UNSUPPORTED_PROTOCOL_VERSION")

    def test_missing_method_surface_fails_before_any_call(self) -> None:
        for import_name, factory in (
            ("langchain_core", instrument_langchain_runnable),
            ("langgraph", instrument_langgraph),
            ("crewai", instrument_crewai),
            ("semantic_kernel", instrument_semantic_kernel),
            ("mcp", instrument_mcp_client),
        ):
            with self.subTest(import_name=import_name), self.fake_module(import_name):
                with self.assertRaises(IntegrationContractError) as caught:
                    factory(object())
                self.assertEqual(caught.exception.code, "INVALID_INTEGRATION_SURFACE")

    def test_every_bounded_method_preserves_framework_exception_identity(self) -> None:
        private_message = "PRIVATE_FRAMEWORK_EXCEPTION"
        cases = (
            (
                "langchain_core",
                instrument_langchain_runnable,
                FailureDual,
                (lambda adapter: adapter.invoke(), lambda adapter: asyncio.run(adapter.ainvoke())),
            ),
            (
                "langgraph",
                instrument_langgraph,
                FailureDual,
                (lambda adapter: adapter.invoke(), lambda adapter: asyncio.run(adapter.ainvoke())),
            ),
            (
                "crewai",
                instrument_crewai,
                FailureCrew,
                (lambda adapter: adapter.kickoff(), lambda adapter: asyncio.run(adapter.kickoff_async())),
            ),
            (
                "semantic_kernel",
                instrument_semantic_kernel,
                FailureKernel,
                (lambda adapter: asyncio.run(adapter.invoke()), lambda adapter: asyncio.run(adapter.invoke_prompt())),
            ),
            (
                "mcp",
                instrument_mcp_client,
                FailureMCP,
                (lambda adapter: asyncio.run(adapter.call_tool("local_tool")),),
            ),
        )
        for import_name, factory, target_type, actions in cases:
            with self.subTest(import_name=import_name), self.fake_module(import_name):
                failure = FrameworkFailure(private_message)
                sink = InMemorySpanSink()
                adapter = factory(target_type(failure), sink=sink)
                for action in actions:
                    with self.assertRaises(FrameworkFailure) as caught:
                        action(adapter)
                    self.assertIs(caught.exception, failure)
                evidence = json.dumps(
                    [record.to_dict() for record in sink.records],
                    sort_keys=True,
                )
                self.assertNotIn(private_message, evidence)
                self.assertTrue(all(record.status_code == "ERROR" for record in sink.records))


if __name__ == "__main__":
    unittest.main()
