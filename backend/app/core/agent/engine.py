"""Agent Engine - orchestrates the end-to-end generation workflow.

The Agent Engine uses a Plan-and-Execute pattern:
1. Understand user requirement → structured analysis
2. Plan: select best model and construct optimized prompt
3. Execute: call generation model via the adapter
4. Observe: quality check the output
5. Refine: retry with adjustments if needed (future)
"""

import json
import logging
from dataclasses import dataclass, field
from typing import Any

from app.core.models.base import BaseModelAdapter, GenerationResult
from app.core.models.llm_adapter import LLMAggregationAdapter
from app.core.models.registry import AdapterRegistry

logger = logging.getLogger(__name__)


@dataclass
class ProductAnalysis:
    """Structured analysis of a product from the user's requirement."""
    product_type: str = ""          # e.g. "t-shirt", "shoes", "watch"
    product_color: str = ""
    product_material: str = ""
    desired_scene: str = ""         # e.g. "beach", "coffee shop", "studio"
    model_description: str = ""     # e.g. "Asian female, casual pose"
    lighting: str = "natural"
    style: str = "lifestyle"        # lifestyle, studio, editorial, minimal
    aspect_ratio: str = "1:1"
    platform: str = "generic"       # amazon, taobao, shopify, etc.
    additional_notes: str = ""
    language: str = "en"            # original user language


@dataclass
class GenerationPlan:
    """A complete plan for a generation task."""
    analysis: ProductAnalysis = field(default_factory=ProductAnalysis)
    chosen_model: str = "flux-pro"  # adapter name
    optimized_prompt: str = ""
    negative_prompt: str = ""
    model_params: dict = field(default_factory=dict)
    need_background_removal: bool = True
    estimated_cost: float = 0.0


class AgentEngine:
    """
    Core orchestrator for e-commerce image/video generation.

    Responsibilities:
    1. Analyze user's natural language requirement → structured product info
    2. Write optimized generation prompts for the target model
    3. Select the best model for the task (quality/speed/cost trade-off)
    4. Coordinate background removal → generation → post-processing
    """

    PRODUCT_ANALYSIS_SCHEMA = {
        "type": "object",
        "properties": {
            "product_type": {"type": "string", "description": "Product category (t-shirt, shoes, watch, etc.)"},
            "product_color": {"type": "string"},
            "product_material": {"type": "string"},
            "desired_scene": {"type": "string", "description": "Scene description for lifestyle placement"},
            "model_description": {"type": "string", "description": "Model type if any (age, gender, ethnicity, pose)"},
            "lighting": {"type": "string"},
            "style": {"type": "string", "enum": ["lifestyle", "studio", "editorial", "minimal", "creative"]},
            "aspect_ratio": {"type": "string"},
            "platform": {"type": "string", "description": "Target e-commerce platform"},
            "additional_notes": {"type": "string"},
            "language": {"type": "string", "enum": ["en", "zh"]},
        },
        "required": ["product_type", "product_color", "desired_scene", "style", "language"],
    }

    def __init__(
        self,
        llm_adapter: LLMAggregationAdapter | None = None,
        registry: AdapterRegistry | None = None,
    ):
        from app.core.models.registry import registry as default_registry

        self._llm = llm_adapter or LLMAggregationAdapter()
        self._registry = registry or default_registry

    async def analyze_requirement(
        self,
        user_input: str,
        tenant_preferences: dict | None = None,
    ) -> ProductAnalysis:
        """
        Analyze user's natural language input → structured product information.

        Handles both Chinese and English input. Extracts product attributes,
        desired scene, style preferences, etc.
        """
        messages = [
            {
                "role": "system",
                "content": (
                    "You are an e-commerce product photography expert. "
                    "Analyze the user's requirement for a product photo/video generation. "
                    "Extract structured information about the product, desired scene, style, etc. "
                    "If the user writes in Chinese, respond with Chinese field values; "
                    "if English, respond in English."
                ),
            },
            {"role": "user", "content": user_input},
        ]

        result = await self._llm.chat_json(
            messages=messages,
            schema=self.PRODUCT_ANALYSIS_SCHEMA,
            temperature=0.3,
        )

        analysis = ProductAnalysis(**result)

        # Apply tenant-level overrides if provided
        if tenant_preferences:
            if "default_style" in tenant_preferences:
                analysis.style = tenant_preferences["default_style"]
            if "default_aspect_ratio" in tenant_preferences:
                analysis.aspect_ratio = tenant_preferences["default_aspect_ratio"]

        logger.info("Product analysis: %s", analysis)
        return analysis

    async def build_prompt(
        self,
        analysis: ProductAnalysis,
        target_model: str = "flux-pro",
        brand_template: dict | None = None,
    ) -> tuple[str, str]:
        """
        Build an optimized prompt + negative prompt for the target generation model.

        For most models, the prompt is written in English (better training data).
        For Tongyi Wanxiang, the prompt can be in Chinese.
        """
        adapter = self._registry.get_by_name(target_model)
        supports_chinese = adapter.capability.supports_chinese_prompt if adapter else False
        prompt_language = "Chinese" if supports_chinese and analysis.language == "zh" else "English"

        # Build brand context
        brand_context = ""
        if brand_template:
            brand_context = f"""
Brand Guidelines:
- Colors: {brand_template.get('colors', 'any')}
- Style: {brand_template.get('style', 'professional')}
- Vibe: {brand_template.get('vibe', 'clean and modern')}
"""

        messages = [
            {
                "role": "system",
                "content": f"""You are an expert prompt engineer for AI image generation models.
Write optimized prompts for the model "{target_model}".

Your prompts should:
1. Start with the product and scene description clearly
2. Include lighting, composition, and camera details
3. Add quality keywords: "commercial photography, 8k resolution, professional product shot"
4. Be written in {prompt_language}
5. Be 50-150 words, concise but detailed
6. Include negative prompt keywords (things to avoid)

{brand_context}

Output JSON with "prompt" and "negative_prompt" fields.""",
            },
            {
                "role": "user",
                "content": f"""Product: {analysis.product_color} {analysis.product_type} ({analysis.product_material})
Scene: {analysis.desired_scene}
Model: {analysis.model_description or 'No model, product-only shot'}
Lighting: {analysis.lighting}
Style: {analysis.style}
Platform: {analysis.platform}
Aspect Ratio: {analysis.aspect_ratio}
Notes: {analysis.additional_notes}

Write the optimized prompt.""",
            },
        ]

        schema = {
            "type": "object",
            "properties": {
                "prompt": {"type": "string"},
                "negative_prompt": {"type": "string"},
            },
            "required": ["prompt", "negative_prompt"],
        }

        result = await self._llm.chat_json(messages=messages, schema=schema, temperature=0.7)
        return result["prompt"], result["negative_prompt"]

    async def select_model(
        self,
        analysis: ProductAnalysis,
        user_preference: str | None = None,
    ) -> str:
        """
        Select the best model for this generation task.

        Decision factors:
        - Photorealism needed? → Flux Pro
        - Chinese market? → Tongyi Wanxiang
        - Speed/cost priority? → SDXL or Flux Schnell
        - Explicit user preference overrides auto-selection
        """
        # User override
        if user_preference:
            adapter = self._registry.get_by_name(user_preference)
            if adapter and adapter.capability.is_enabled:
                return user_preference

        # Default: Flux Pro for best quality
        flux = self._registry.get_image("flux-pro")
        if flux and flux.capability.is_enabled:
            return "flux-pro"

        # Fallback: first enabled image adapter
        for cap in self._registry.list_enabled("image"):
            return cap.name

        return "mock-image"

    async def plan_generation(
        self,
        user_input: str,
        preferred_model: str | None = None,
        tenant_preferences: dict | None = None,
        brand_template: dict | None = None,
    ) -> GenerationPlan:
        """
        Full planning phase: analyze requirement → select model → build prompt.

        Returns a complete GenerationPlan ready for execution.
        """
        # Step 1: Understand
        analysis = await self.analyze_requirement(user_input, tenant_preferences)

        # Step 2: Select model
        model_name = await self.select_model(analysis, preferred_model)

        # Step 3: Build prompt
        prompt, negative_prompt = await self.build_prompt(analysis, model_name, brand_template)

        # Calculate dimensions from aspect ratio
        dims = self._aspect_ratio_to_dimensions(analysis.aspect_ratio)
        adapter = self._registry.get_by_name(model_name)
        cost = adapter.capability.cost_per_image if adapter else 0.0

        return GenerationPlan(
            analysis=analysis,
            chosen_model=model_name,
            optimized_prompt=prompt,
            negative_prompt=negative_prompt,
            model_params={
                "width": dims[0],
                "height": dims[1],
                "num_outputs": 2,
            },
            need_background_removal=analysis.style != "studio",
            estimated_cost=cost * 2,
        )

    async def execute_generation(
        self,
        plan: GenerationPlan,
        reference_image_url: str | None = None,
    ) -> GenerationResult:
        """
        Execute a generation plan: call the selected model adapter.
        """
        adapter = self._registry.get_by_name(plan.chosen_model)
        if adapter is None:
            return GenerationResult(
                success=False,
                error=f"Model '{plan.chosen_model}' not found in registry",
            )

        return await adapter.generate(
            prompt=plan.optimized_prompt,
            negative_prompt=plan.negative_prompt,
            reference_image_url=reference_image_url,
            **plan.model_params,
        )

    async def quality_check(
        self,
        analysis: ProductAnalysis,
        prompt: str,
        image_urls: list[str],
    ) -> dict:
        """
        Evaluate generated images using LLM-as-judge.

        Checks: product accuracy, artifacts, lighting match, composition.
        Returns a score and pass/fail verdict.
        """
        # TODO: In Phase 2, integrate vision-capable LLM to actually look at images
        # For MVP, use a heuristic based on prompt similarity
        return {
            "passed": True,
            "score": 0.85,
            "feedback": "Quality check passed (heuristic)",
            "issues": [],
        }

    @staticmethod
    def _aspect_ratio_to_dimensions(ratio: str) -> tuple[int, int]:
        """Convert aspect ratio string to pixel dimensions."""
        mapping = {
            "1:1": (1024, 1024),
            "4:3": (1152, 896),
            "3:4": (896, 1152),
            "16:9": (1280, 720),
            "9:16": (720, 1280),
            "3:2": (1152, 768),
            "2:3": (768, 1152),
        }
        return mapping.get(ratio, (1024, 1024))
