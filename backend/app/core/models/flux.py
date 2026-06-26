"""Flux image generation adapter via Replicate."""

from typing import Any

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from app.config import get_settings
from app.core.models.base import AdapterCapability, BaseModelAdapter, GenerationResult


class FluxAdapter(BaseModelAdapter):
    """
    Flux Pro image generation adapter via Replicate.

    Flux is currently the best open-weight model for photorealistic
    product/lifestyle image generation.
    """

    def __init__(self, enabled: bool = True):
        settings = get_settings()
        self._api_base = settings.flux_api_base.rstrip("/")
        self._api_key = settings.flux_api_key or settings.replicate_api_key
        self._enabled = enabled
        self._client: httpx.AsyncClient | None = None

    @property
    def capability(self) -> AdapterCapability:
        return AdapterCapability(
            name="flux-pro",
            provider="black-forest-labs",
            provider_type="image",
            description="Flux Pro - photorealistic product and lifestyle image generation",
            max_resolution="1024x1024",
            supported_sizes=["1024x1024", "1024x576", "576x1024", "768x768"],
            cost_per_image=0.05,
            supports_chinese_prompt=False,
            best_for=["lifestyle", "photorealistic", "complex scenes", "product display"],
            is_enabled=self._enabled,
        )

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(
                timeout=httpx.Timeout(300.0),
                headers={
                    "Authorization": f"Bearer {self._api_key}",
                    "Content-Type": "application/json",
                },
            )
        return self._client

    @retry(stop=stop_after_attempt(2), wait=wait_exponential(multiplier=1, min=5, max=30))
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
        Generate images via Flux on Replicate.

        Uses the 'black-forest-labs/flux-pro' model or the smaller
        'black-forest-labs/flux-schnell' for faster/cheaper results.
        """
        client = await self._get_client()

        model_version = kwargs.get(
            "model_version", "black-forest-labs/flux-1.1-pro"
        )

        input_params: dict[str, Any] = {
            "prompt": prompt,
            "width": width,
            "height": height,
            "num_outputs": num_outputs,
            "output_format": "png",
        }

        if negative_prompt:
            input_params["negative_prompt"] = negative_prompt

        if reference_image_url:
            input_params["image"] = reference_image_url
            input_params["prompt_strength"] = kwargs.get("prompt_strength", 0.8)

        # Extra params
        input_params["num_inference_steps"] = kwargs.get("steps", 28)
        input_params["guidance_scale"] = kwargs.get("guidance_scale", 3.5)
        input_params["seed"] = kwargs.get("seed")

        payload = {
            "version": model_version,
            "input": {k: v for k, v in input_params.items() if v is not None},
        }

        # Create prediction
        resp = await client.post(f"{self._api_base}/predictions", json=payload)
        resp.raise_for_status()
        prediction = resp.json()

        # Poll until complete
        prediction_id = prediction["id"]
        poll_url = f"{self._api_base}/predictions/{prediction_id}"

        max_polls = 60  # ~5 minutes max
        for _ in range(max_polls):
            import asyncio
            await asyncio.sleep(5)
            resp = await client.get(poll_url)
            resp.raise_for_status()
            prediction = resp.json()

            status = prediction.get("status")
            if status == "succeeded":
                urls = prediction.get("output", [])
                if isinstance(urls, str):
                    urls = [urls]

                return GenerationResult(
                    success=True,
                    urls=urls,
                    metadata={
                        "model": model_version,
                        "prediction_id": prediction_id,
                        "seed": prediction.get("input", {}).get("seed"),
                        "metrics": prediction.get("metrics", {}),
                    },
                )
            elif status in ("failed", "canceled"):
                return GenerationResult(
                    success=False,
                    error=prediction.get("error", "Generation failed"),
                )

        return GenerationResult(
            success=False,
            error="Timed out waiting for generation to complete",
        )

    async def close(self) -> None:
        if self._client:
            await self._client.aclose()
            self._client = None
