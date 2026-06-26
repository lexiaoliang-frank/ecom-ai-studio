"""Model Gateway package - adapter pattern for image/video/LLM providers."""

from app.core.models.base import (
    AdapterCapability,
    BaseLLMAdapter,
    BaseModelAdapter,
    GenerationResult,
)
from app.core.models.dall_e import DALLEAdapter
from app.core.models.flux import FluxAdapter
from app.core.models.llm_adapter import LLMAggregationAdapter
from app.core.models.mock import MockImageAdapter
from app.core.models.registry import AdapterRegistry, registry

__all__ = [
    "BaseModelAdapter",
    "BaseLLMAdapter",
    "AdapterCapability",
    "GenerationResult",
    "AdapterRegistry",
    "registry",
    "LLMAggregationAdapter",
    "FluxAdapter",
    "DALLEAdapter",
    "MockImageAdapter",
]
