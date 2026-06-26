"""Celery task definitions for image and video generation."""

import logging
import uuid
from typing import Any

from workers.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(bind=True, name="generate_image_task")
def generate_image_task(
    self,
    tenant_id: str,
    user_input: str,
    reference_image_url: str | None = None,
    preferred_model: str | None = None,
    project_id: str | None = None,
    task_id: str | None = None,
    tenant_preferences: dict | None = None,
    **kwargs: Any,
) -> dict:
    """
    Async task: generate an image using the full pipeline.

    This runs inside a Celery worker process.
    """
    task_id = task_id or str(uuid.uuid4())
    logger.info("Starting image generation task %s for tenant %s", task_id, tenant_id)

    try:
        # Import here to avoid circular imports at module level
        import asyncio

        from app.core.generation.image import ImageGenerationService
        from app.core.models.mock import MockImageAdapter
        from app.core.models.registry import registry
        from app.db.models.generation_task import GenerationTask
        from app.db.session import AsyncSessionLocal

        # Ensure at least mock adapter is registered for dev
        if not registry._image_adapters:
            registry.register_image("mock-image", MockImageAdapter())

        # Run the async pipeline
        async def run_pipeline():
            service = ImageGenerationService(registry=registry)

            # Download reference image if URL provided
            reference_data = None
            if reference_image_url:
                import httpx

                async with httpx.AsyncClient() as client:
                    resp = await client.get(reference_image_url)
                    if resp.status_code == 200:
                        reference_data = resp.content

            result, plan = await service.generate(
                user_input=user_input,
                reference_image_data=reference_data,
                reference_image_url=reference_image_url,
                preferred_model=preferred_model,
                tenant_preferences=tenant_preferences,
            )

            # Persist to DB
            async with AsyncSessionLocal() as db:
                try:
                    task_record = await service.create_task_record(
                        db=db,
                        tenant_id=uuid.UUID(tenant_id),
                        user_input=user_input,
                        result=result,
                        plan=plan,
                        project_id=uuid.UUID(project_id) if project_id else None,
                    )
                    task_record.id = uuid.UUID(task_id)
                    task_record.status = "completed" if result.success else "failed"

                    if result.success:
                        assets = await service.create_asset_records(
                            db=db,
                            tenant_id=uuid.UUID(tenant_id),
                            result=result,
                            task_id=task_record.id,
                            project_id=uuid.UUID(project_id) if project_id else None,
                        )
                        result.metadata["asset_ids"] = [str(a.id) for a in assets]

                    await db.commit()
                except Exception as e:
                    await db.rollback()
                    logger.error("Failed to persist task: %s", e)

            return {
                "task_id": task_id,
                "status": "completed" if result.success else "failed",
                "result_urls": result.urls,
                "metadata": result.metadata,
                "error": result.error,
                "optimized_prompt": plan.optimized_prompt,
                "model_used": plan.chosen_model,
                "estimated_cost": plan.estimated_cost,
            }

        return asyncio.run(run_pipeline())

    except Exception as e:
        logger.exception("Task %s failed: %s", task_id, str(e))
        return {
            "task_id": task_id,
            "status": "failed",
            "error": str(e),
            "result_urls": [],
        }


@celery_app.task(bind=True, name="generate_batch_task")
def generate_batch_task(
    self,
    tenant_id: str,
    batch_items: list[dict],
    project_id: str | None = None,
) -> dict:
    """
    Async task: process a batch of image generations.

    Each item in batch_items should have:
    - user_input: str (requirement for this SKU)
    - reference_image_url: str | None
    - sku_id: str | None (for tracking)
    """
    logger.info("Starting batch generation: %d items", len(batch_items))
    results = []

    for i, item in enumerate(batch_items):
        result = generate_image_task.delay(
            tenant_id=tenant_id,
            user_input=item.get("user_input", ""),
            reference_image_url=item.get("reference_image_url"),
            project_id=project_id,
            tenant_preferences=item.get("preferences"),
        )
        results.append({
            "sku_id": item.get("sku_id", str(i)),
            "task_id": result.id,
        })

    return {
        "batch_status": "submitted",
        "total_items": len(batch_items),
        "tasks": results,
    }
