"""Model adapter registry - enables dynamic model discovery and selection."""

from app.core.models.base import AdapterCapability, BaseLLMAdapter, BaseModelAdapter


class AdapterRegistry:
    """Registry of all available model adapters, queryable by capability."""

    def __init__(self):
        self._image_adapters: dict[str, BaseModelAdapter] = {}
        self._video_adapters: dict[str, BaseModelAdapter] = {}
        self._llm_adapters: dict[str, BaseLLMAdapter] = {}
        self._postprocess_adapters: dict[str, BaseModelAdapter] = {}

    def register_image(self, name: str, adapter: BaseModelAdapter) -> None:
        self._image_adapters[name] = adapter

    def register_video(self, name: str, adapter: BaseModelAdapter) -> None:
        self._video_adapters[name] = adapter

    def register_llm(self, name: str, adapter: BaseLLMAdapter) -> None:
        self._llm_adapters[name] = adapter

    def register_postprocess(self, name: str, adapter: BaseModelAdapter) -> None:
        self._postprocess_adapters[name] = adapter

    def get_image(self, name: str) -> BaseModelAdapter | None:
        return self._image_adapters.get(name)

    def get_video(self, name: str) -> BaseModelAdapter | None:
        return self._video_adapters.get(name)

    def get_llm(self, name: str = "default") -> BaseLLMAdapter | None:
        return self._llm_adapters.get(name)

    def get_by_name(self, name: str) -> BaseModelAdapter | None:
        """Look up any adapter by name across all registries."""
        all_adapters = {
            **self._image_adapters,
            **self._video_adapters,
            **self._postprocess_adapters,
        }
        return all_adapters.get(name)

    def list_image_capabilities(self) -> list[AdapterCapability]:
        return [a.capability for a in self._image_adapters.values()]

    def list_video_capabilities(self) -> list[AdapterCapability]:
        return [a.capability for a in self._video_adapters.values()]

    def list_all_capabilities(self) -> list[AdapterCapability]:
        caps = (
            self.list_image_capabilities()
            + self.list_video_capabilities()
            + [BaseModelAdapter.__dict__.get("capability") for a in self._postprocess_adapters.values()]
        )
        return [c for c in caps if c is not None]

    def list_enabled(self, provider_type: str | None = None) -> list[AdapterCapability]:
        """List enabled adapters, optionally filtered by type."""
        if provider_type == "image":
            caps = self.list_image_capabilities()
        elif provider_type == "video":
            caps = self.list_video_capabilities()
        else:
            caps = self.list_all_capabilities()
        return [c for c in caps if c.is_enabled]


# Global singleton
registry = AdapterRegistry()
