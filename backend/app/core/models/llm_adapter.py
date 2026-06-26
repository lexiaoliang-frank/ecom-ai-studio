"""LLM adapter for aggregation platforms (Tokenpony, OpenRouter, etc.).

Uses OpenAI-compatible API format so switching providers is just changing
the base URL and API key in config. No code changes needed.
"""

import json
from typing import Any

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from app.config import get_settings
from app.core.models.base import BaseLLMAdapter


class LLMAggregationAdapter(BaseLLMAdapter):
    """
    Adapter for LLM aggregation platforms that support OpenAI-compatible API.

    Works with: Tokenpony, OpenRouter, DeepSeek API, OpenAI API, etc.
    Change LLM_API_BASE and LLM_API_KEY in .env to switch providers.
    """

    def __init__(self, name: str = "default"):
        settings = get_settings()
        self._name = name
        self._api_base = settings.llm_api_base.rstrip("/")
        self._api_key = settings.llm_api_key
        self._default_model = settings.llm_model
        self._cheap_model = settings.llm_model_cheap
        self._client: httpx.AsyncClient | None = None

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

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=30))
    async def chat(
        self,
        messages: list[dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 2048,
        model: str | None = None,
        **kwargs: Any,
    ) -> str:
        """
        Send a chat completion request.

        Args:
            messages: List of {"role": "...", "content": "..."} dicts
            temperature: Sampling temperature
            max_tokens: Max output tokens
            model: Model name override (uses default if None)

        Returns:
            Model's text response
        """
        client = await self._get_client()
        model_name = model or self._default_model

        payload = {
            "model": model_name,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            **kwargs,
        }

        response = await client.post(f"{self._api_base}/chat/completions", json=payload)
        response.raise_for_status()
        data = response.json()
        return data["choices"][0]["message"]["content"]

    async def chat_json(
        self,
        messages: list[dict[str, str]],
        schema: dict,
        temperature: float = 0.3,
        model: str | None = None,
        **kwargs: Any,
    ) -> dict:
        """
        Send a chat completion that returns structured JSON.

        For models that don't support native JSON mode, we append instructions
        to the system prompt and parse the response. For models that support
        response_format, we use it directly.
        """
        client = await self._get_client()
        model_name = model or self._default_model

        # Append JSON formatting instructions to the last system message
        json_instruction = f"\n\nYou MUST respond with valid JSON matching this schema:\n{json.dumps(schema, indent=2, ensure_ascii=False)}\nRespond ONLY with the JSON object, no other text."
        for msg in messages:
            if msg["role"] == "system":
                msg["content"] += json_instruction
                break
        else:
            messages.insert(0, {"role": "system", "content": json_instruction.strip()})

        # Try native JSON mode if supported
        payload: dict[str, Any] = {
            "model": model_name,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": kwargs.pop("max_tokens", 4096),
            "response_format": {"type": "json_object"},
            **kwargs,
        }

        try:
            response = await client.post(
                f"{self._api_base}/chat/completions", json=payload
            )
            response.raise_for_status()
            data = response.json()
            content = data["choices"][0]["message"]["content"]
            return json.loads(content)
        except (json.JSONDecodeError, KeyError):
            # Fallback: remove json_object format and retry
            payload.pop("response_format", None)
            response = await client.post(
                f"{self._api_base}/chat/completions", json=payload
            )
            response.raise_for_status()
            data = response.json()
            content = data["choices"][0]["message"]["content"]
            # Extract JSON from potential markdown code block
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0]
            elif "```" in content:
                content = content.split("```")[1].split("```")[0]
            return json.loads(content.strip())

    async def close(self) -> None:
        if self._client:
            await self._client.aclose()
            self._client = None
