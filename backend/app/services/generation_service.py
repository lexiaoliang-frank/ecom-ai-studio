"""Generation service - business logic layer between API and Agent Engine."""

import logging
import uuid
from typing import Optional

from celery.result import AsyncResult

from app.core.agent.engine import AgentEngine
from app.core.generation.image import ImageGenerationService
from app.core.models.mock import MockImageAdapter
from app.core.models.registry import registry

logger = logging.getLogger(__name__)

# Initialize registry with development adapters
def _init_registry():
    if not registry._image_adapters:
        registry.register_image("mock-image", MockImageAdapter(delay_seconds=0.5))
        logger.info("Registered mock-image adapter for development")

_init_registry()


class GenerationService:
    """Service layer for generation operations."""

    def __init__(self):
        self._image_service = ImageGenerationService(registry=registry)

    def submit_image_generation(
        self,
        tenant_id: uuid.UUID,
        user_input: str,
        reference_image_url: str | None = None,
        preferred_model: str | None = None,
        project_id: uuid.UUID | None = None,
    ) -> str:
        """
        Submit an image generation task to the queue.

        Returns the task ID for polling.
        """
        from workers.tasks.generation import generate_image_task

        celery_task = generate_image_task.delay(
            tenant_id=str(tenant_id),
            user_input=user_input,
            reference_image_url=reference_image_url,
            preferred_model=preferred_model,
            project_id=str(project_id) if project_id else None,
        )

        return celery_task.id

    def submit_batch_generation(
        self,
        tenant_id: uuid.UUID,
        batch_items: list[dict],
        project_id: uuid.UUID | None = None,
    ) -> str:
        """
        Submit a batch of image generation tasks.

        Each item: {"user_input": "...", "reference_image_url": "...", "sku_id": "..."}
        """
        from workers.tasks.generation import generate_batch_task

        celery_task = generate_batch_task.delay(
            tenant_id=str(tenant_id),
            batch_items=batch_items,
            project_id=str(project_id) if project_id else None,
        )

        return celery_task.id

    def get_task_status(self, task_id: str) -> dict:
        """Get the status of a generation task."""
        result = AsyncResult(task_id)

        response = {
            "task_id": task_id,
            "status": result.state.lower() if result.state else "unknown",
            "progress": 0.0,
        }

        if result.ready():
            task_result = result.result
            if isinstance(task_result, dict):
                response.update({
                    "status": task_result.get("status", result.state.lower()),
                    "result_urls": task_result.get("result_urls", []),
                    "error_message": task_result.get("error"),
                    "progress": 1.0,
                })

        elif result.state == "STARTED":
            response["progress"] = 0.5

        return response

    def cancel_task(self, task_id: str) -> bool:
        """Cancel a pending or running task."""
        result = AsyncResult(task_id)
        if result.state in ("PENDING", "STARTED", "RETRY"):
            result.revoke(terminate=True)
            return True
        return False
