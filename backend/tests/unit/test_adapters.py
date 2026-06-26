"""Tests for Model Gateway adapters."""

import pytest
from unittest.mock import AsyncMock, patch

from app.core.models.base import AdapterCapability, GenerationResult
from app.core.models.mock import MockImageAdapter
from app.core.models.registry import AdapterRegistry


class TestMockAdapter:
    async def test_generate_returns_success(self):
        adapter = MockImageAdapter(delay_seconds=0)
        result = await adapter.generate(prompt="test product on beach")
        assert result.success
        assert len(result.urls) == 1
        assert result.cost == 0.0

    async def test_generate_multiple_outputs(self):
        adapter = MockImageAdapter(delay_seconds=0)
        result = await adapter.generate(prompt="test", num_outputs=3)
        assert result.success
        assert len(result.urls) == 3

    async def test_capability(self):
        adapter = MockImageAdapter()
        cap = adapter.capability
        assert cap.provider_type == "image"
        assert cap.is_enabled is True


class TestAdapterRegistry:
    def test_register_and_get(self):
        registry = AdapterRegistry()
        adapter = MockImageAdapter()
        registry.register_image("mock-image", adapter)
        assert registry.get_image("mock-image") is adapter

    def test_list_enabled(self):
        registry = AdapterRegistry()
        registry.register_image("mock-image", MockImageAdapter(enabled=True))
        caps = registry.list_enabled("image")
        assert len(caps) == 1
        assert caps[0].name == "mock-image"

    def test_get_by_name_cross_registry(self):
        registry = AdapterRegistry()
        registry.register_image("img", MockImageAdapter())
        assert registry.get_by_name("img") is not None
        assert registry.get_by_name("nonexistent") is None


class TestGenerationResult:
    def test_success_result(self):
        result = GenerationResult(success=True, urls=["http://example.com/img.png"])
        assert result.success
        assert len(result.urls) == 1

    def test_failure_result(self):
        result = GenerationResult(success=False, error="API error")
        assert not result.success
        assert result.error == "API error"
