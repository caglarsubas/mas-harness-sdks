"""Optional, tenant-neutral framework invocation adapters.

Importing this module never imports an optional framework. Framework-specific
modules perform their one declared import only when their factory is called.
"""

from ._base import (
    INTEGRATION_SPECS,
    IntegrationContractError,
    IntegrationSpec,
    IntegrationUnavailableError,
)
from .vector import instrument_async_vector_search, instrument_vector_search

__all__ = [
    "INTEGRATION_SPECS",
    "IntegrationContractError",
    "IntegrationSpec",
    "IntegrationUnavailableError",
    "instrument_async_vector_search",
    "instrument_vector_search",
]
