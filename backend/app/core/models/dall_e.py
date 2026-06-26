"""DALL·E 3 image generation adapter via OpenAI API."""

from typing import Any

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from app.config import get_settings
from app.core.models.base import AdapterCapability, BaseModelAdapter, GenerationResult


class DALLEAdapter(BaseModelAdapter):
    """DALL·E 3 adapter via OpenAI API (or compatible)."""

    def __init__(self, enabled: bool = False):
        settings = get_settings()
        self._api_key = settings.openai_api_key
        self._api_base = "https://api.openai.com/v1"
        self._enabled = enabled
        self._client: httpx.AsyncClient | None = None

    @property
    def capability(self) -> AdapterCapability:
        return AdapterCapability(
            name="dall-e-3",
            provider="openai",
            provider_type="image",
            description="DALL·E 3 - OpenAI's latest image generation model",
            max_resolution="1024x1024",
            supported_sizes=["1024x1024", "1024x1792", "1792x1024"],
            cost_per_image=0.04,
            supports_chinese_prompt=False,
            best_for=["conceptual", "creative", "illustrated style"],
            is_enabled=self._enabled,
        )

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(
                timeout=httpx.Timeout(120.0),
                headers={
                    "Authorization": f"Bearer {self._api_key}",
                    "Content-Type": "application/json",
                },
            )
        return self._client

    @retry(stop=stop_after_attempt(2), wait=wait_exponential(multiplier=1, min=2, max=15))
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
        client = await self._get_client()

        size = "1024x1024"
        if width == 1792 and height == 1024:
            size = "1792x1024"
        elif width == 1024 and height == 1792:
            size = "1024x1792"

        quality = kwargs.get("quality", "standard")  # standard or hd
        style = kwargs.get("style", "vivid")  # vivid or natural

        payload = {
            "model": "dall-e-3",
            "prompt": prompt,
            "n": min(num_outputs, 1),  # DALL-E 3 only supports n=1
            "size": size,
            "quality": quality,
            "style": style,
        }

        resp = await client.post(
            f"{self._api_base}/images/generations", json=payload
        )
        resp.raise_for_status()
        data = resp.json()

        urls = [img["url"] for img in data.get("data", [])]

        return GenerationResult(
            success=True,
            urls=urls,
            metadata={
                "model": "dall-e-3",
                "quality": quality,
                "style": style,
                "revised_prompt": data.get("data", [{}])[0].get("revised_prompt", ""),
            },
            cost=0.04 if quality == "standard" else 0.08,
        )

    async def close(self) -> None:
        if self._client:
            await self._client.aclose()
            self._client = None
