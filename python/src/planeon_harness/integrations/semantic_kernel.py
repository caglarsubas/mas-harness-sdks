"""Bounded Semantic Kernel invocation adapter."""

from __future__ import annotations

from typing import Any

from planeon_harness.decorators import SpanSink

from ._base import invoke_async, require_integration, require_methods


class SemanticKernelAdapter:
    """Expose only the admitted asynchronous kernel methods."""

    __slots__ = ("_kernel", "_sink")

    def __init__(self, kernel: object, sink: SpanSink | None) -> None:
        self._kernel = kernel
        self._sink = sink

    async def invoke(self, *args: Any, **kwargs: Any) -> Any:
        return await invoke_async(
            self._kernel.invoke,
            "harness.integration.semantic_kernel.invoke",
            self._sink,
            args,
            kwargs,
        )

    async def invoke_prompt(self, *args: Any, **kwargs: Any) -> Any:
        return await invoke_async(
            self._kernel.invoke_prompt,
            "harness.integration.semantic_kernel.invoke_prompt",
            self._sink,
            args,
            kwargs,
        )


def instrument_semantic_kernel(
    kernel: object,
    *,
    sink: SpanSink | None = None,
) -> SemanticKernelAdapter:
    """Validate Semantic Kernel availability and return an inert adapter."""

    require_integration("semantic_kernel")
    require_methods("semantic_kernel", kernel, ("invoke", "invoke_prompt"))
    return SemanticKernelAdapter(kernel, sink)
