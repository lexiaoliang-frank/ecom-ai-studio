"""Mock adapter for development and testing without real API keys."""

import base64
import time
import uuid
from typing import Any

from app.core.models.base import AdapterCapability, BaseModelAdapter, GenerationResult


class MockImageAdapter(BaseModelAdapter):
    """
    Mock adapter that generates placeholder images for development.

    Returns a 1x1 transparent PNG as a base64 data URL - sufficient for
    testing the full pipeline without consuming API credits.
    """

    # Minimal valid PNG (1x1 transparent pixel)
    _PLACEHOLDER_PNG = base64.b64decode(
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk"
        "+P+/HgAEhQJYhCHsFwAAAABJRU5ErkJggg=="
    )

    def __init__(self, enabled: bool = True, delay_seconds: float = 1.0):
        self._enabled = enabled
        self._delay = delay_seconds

    @property
    def capability(self) -> AdapterCapability:
        return AdapterCapability(
            name="mock-image",
            provider="mock",
            provider_type="image",
            description="Mock adapter - returns placeholder images for development/testing",
            max_resolution="1024x1024",
            supported_sizes=["1024x1024", "512x512"],
            cost_per_image=0.0,
            supports_chinese_prompt=True,
            best_for=["development", "testing"],
            is_enabled=self._enabled,
        )

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
        """Simulate generation with a delay, then return placeholder URLs."""
        if self._delay > 0:
            time.sleep(self._delay)

        placeholder_url = (
            "data:image/png;base64,"
            "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+P+/HgAEhQJYhCHsFwAAAABJRU5ErkJggg=="
        )

        return GenerationResult(
            success=True,
            urls=[placeholder_url] * num_outputs,
            storage_keys=[f"mock/{uuid.uuid4()}.png" for _ in range(num_outputs)],
            metadata={
                "model": "mock-image",
                "prompt_used": prompt,
                "is_mock": True,
            },
            cost=0.0,
        )

    async def health_check(self) -> bool:
        return True
