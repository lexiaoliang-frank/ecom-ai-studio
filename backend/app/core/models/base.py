"""Abstract base class for all model adapters (image, video, LLM, post-process)."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

from pydantic import BaseModel


class GenerationResult(BaseModel):
    """Unified result from any generation adapter."""
    success: bool
    urls: list[str] = []
    storage_keys: list[str] = []
    metadata: dict = {}
    cost: float = 0.0
    error: str | None = None


@dataclass
class AdapterCapability:
    """Describes what a model adapter can do."""
    name: str
    provider: str              # e.g. "openai", "runway", "replicate"
    provider_type: str         # "image", "video", "llm", "postprocess"
    description: str = ""
    max_resolution: str = "1024x1024"
    supported_sizes: list[str] = field(default_factory=lambda: ["1024x1024"])
    cost_per_image: float = 0.0
    cost_per_second: float = 0.0
    supports_chinese_prompt: bool = False
    best_for: list[str] = field(default_factory=list)
    is_enabled: bool = True


class BaseModelAdapter(ABC):
    """
    Abstract base for all generation model adapters.

    Each adapter wraps a specific image/video generation API behind a unified interface.
    Adding a new model = write one new adapter, implement generate(), done.
    """

    @property
    @abstractmethod
    def capability(self) -> AdapterCapability:
        """Return this adapter's capabilities."""

    @abstractmethod
    async def generate(
        self,
        prompt: str,
        negative_prompt: str = "",
        width: int = 1024,
        height: int = 1024,
        num_outputs: int = 1,
        reference_image_url: str | None = None,
        **kwargs: Any,
    ) -> GenerationResult:
        """
        Generate images or video from a prompt.

        Args:
            prompt: The optimized generation prompt
            negative_prompt: What to avoid (mainly for SD/Flux)
            width, height: Output dimensions
            num_outputs: How many to generate (1-4)
            reference_image_url: Optional reference image for img2img or video-from-image
            **kwargs: Model-specific parameters (seed, steps, guidance_scale, etc.)

        Returns:
            GenerationResult with URLs and metadata
        """

    async def health_check(self) -> bool:
        """Check if the adapter's API is reachable and credentials are valid."""
        try:
            result = await self.generate(prompt="test", num_outputs=1)
            return result.success
        except Exception:
            return False


class BaseLLMAdapter(ABC):
    """
    Abstract base for LLM adapters (prompt writing, classification, quality check).

    Uses OpenAI-compatible API format for maximum compatibility with aggregation platforms.
    """

    @abstractmethod
    async def chat(
        self,
        messages: list[dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 2048,
        model: str | None = None,
        **kwargs: Any,
    ) -> str:
        """Send a chat completion request and return the text response."""

    @abstractmethod
    async def chat_json(
        self,
        messages: list[dict[str, str]],
        schema: dict,
        temperature: float = 0.3,
        model: str | None = None,
        **kwargs: Any,
    ) -> dict:
        """Send a chat completion request and parse structured JSON output."""
