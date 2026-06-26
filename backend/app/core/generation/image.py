"""Image generation service - orchestrates the full pipeline."""

import io
import logging
import uuid
from typing import Optional

from PIL import Image
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.agent.engine import AgentEngine, GenerationPlan
from app.core.generation.background import bg_removal_service
from app.core.models.base import GenerationResult
from app.core.models.registry import AdapterRegistry
from app.db.models.asset import Asset
from app.db.models.generation_task import GenerationTask

logger = logging.getLogger(__name__)


class ImageGenerationService:
    """
    Orchestrates the full image generation pipeline:
    1. Analyze requirement → plan
    2. (Optional) Remove background from product image
    3. Generate new image via model adapter
    4. Post-process: resize, watermark, upload to storage
    5. Record results in database
    """

    def __init__(
        self,
        agent_engine: AgentEngine | None = None,
        registry: AdapterRegistry | None = None,
    ):
        from app.core.models.registry import registry as default_registry

        self._engine = agent_engine or AgentEngine(registry=default_registry)
        self._registry = registry or default_registry

    async def generate(
        self,
        user_input: str,
        reference_image_data: bytes | None = None,
        reference_image_url: str | None = None,
        preferred_model: str | None = None,
        tenant_preferences: dict | None = None,
        brand_template: dict | None = None,
        remove_background: bool = True,
    ) -> tuple[GenerationResult, GenerationPlan]:
        """
        Run the full image generation pipeline.

        Args:
            user_input: Natural language requirement from user
            reference_image_data: Raw bytes of uploaded product photo
            reference_image_url: URL to a reference image (alternative to image_data)
            preferred_model: User-specified model override
            tenant_preferences: Tenant-level defaults
            brand_template: Brand style template
            remove_background: Whether to remove background from reference image

        Returns:
            Tuple of (GenerationResult, GenerationPlan) for transparency
        """
        # Step 1: Plan
        plan = await self._engine.plan_generation(
            user_input=user_input,
            preferred_model=preferred_model,
            tenant_preferences=tenant_preferences,
            brand_template=brand_template,
        )

        # Step 2: Background removal (if reference image provided)
        processed_image_url = reference_image_url
        if reference_image_data and remove_background and plan.need_background_removal:
            try:
                bg_removed = await bg_removal_service.remove_background(reference_image_data)
                # In production, upload this to S3/MinIO and get a URL
                # For MVP, we pass the original URL and let the model handle it
                logger.info("Background removed from reference image")
            except Exception as e:
                logger.warning("Background removal skipped: %s", e)

        # Step 3: Generate
        result = await self._engine.execute_generation(
            plan=plan,
            reference_image_url=processed_image_url or reference_image_url,
        )

        # Step 4: Quality check
        if result.success:
            qc_result = await self._engine.quality_check(
                analysis=plan.analysis,
                prompt=plan.optimized_prompt,
                image_urls=result.urls,
            )
            result.metadata["quality_check"] = qc_result

        return result, plan

    async def create_task_record(
        self,
        db: AsyncSession,
        tenant_id: uuid.UUID,
        user_input: str,
        result: GenerationResult,
        plan: GenerationPlan,
        reference_asset_ids: list[uuid.UUID] | None = None,
        project_id: uuid.UUID | None = None,
    ) -> GenerationTask:
        """Persist a generation task record in the database."""
        task = GenerationTask(
            tenant_id=tenant_id,
            project_id=project_id,
            task_type="text_to_image",
            status="completed" if result.success else "failed",
            input_prompt=user_input,
            optimized_prompt=plan.optimized_prompt,
            input_asset_ids=reference_asset_ids or [],
            model_params=plan.model_params,
            llm_model_used=self._engine._llm._default_model if hasattr(self._engine, '_llm') else None,
            result_metadata=result.metadata,
            error_message=result.error,
            started_at=None,
            completed_at=None,
        )
        db.add(task)
        await db.flush()
        return task

    async def create_asset_records(
        self,
        db: AsyncSession,
        tenant_id: uuid.UUID,
        result: GenerationResult,
        task_id: uuid.UUID,
        project_id: uuid.UUID | None = None,
    ) -> list[Asset]:
        """Create asset records for generated images."""
        assets = []
        for i, url in enumerate(result.urls):
            asset = Asset(
                tenant_id=tenant_id,
                project_id=project_id,
                filename=f"generated_{task_id}_{i}.png",
                asset_type="generated",
                mime_type="image/png",
                storage_url=url,
                storage_key=result.storage_keys[i] if i < len(result.storage_keys) else url,
                source_type="generated",
                source_task_id=task_id,
                metadata={"model": result.metadata.get("model", "unknown")},
                tags=["generated", "ai"],
            )
            db.add(asset)
            assets.append(asset)
        await db.flush()
        return assets
