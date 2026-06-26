"""Generation API endpoints - image and video generation."""

import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, UploadFile
from pydantic import BaseModel

from app.db.models.user import User
from app.dependencies import get_current_user, get_tenant_id

router = APIRouter()


class GenerateImageRequest(BaseModel):
    requirement: str
    project_id: Optional[str] = None
    style: Optional[str] = "lifestyle"
    aspect_ratio: Optional[str] = "1:1"
    quality: Optional[str] = "standard"
    model_name: Optional[str] = None
    workflow: Optional[str] = None
    count: int = 1


class GenerateVideoRequest(BaseModel):
    requirement: str
    project_id: Optional[str] = None
    duration: int = 15
    style: Optional[str] = "showcase"
    model_name: Optional[str] = None


class TaskResponse(BaseModel):
    task_id: str
    status: str
    estimated_time_sec: int = 30


class TaskStatusResponse(BaseModel):
    task_id: str
    status: str
    progress: float = 0.0
    preview_url: Optional[str] = None
    result_urls: list[str] = []
    error_message: Optional[str] = None


@router.post("/image", response_model=TaskResponse)
async def generate_image(
    req: GenerateImageRequest,
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    current_user: User = Depends(get_current_user),
):
    """Submit an image generation task to the async queue."""
    from app.services.generation_service import GenerationService

    service = GenerationService()
    task_id = service.submit_image_generation(
        tenant_id=tenant_id,
        user_input=req.requirement,
        preferred_model=req.model_name,
        project_id=uuid.UUID(req.project_id) if req.project_id else None,
    )
    return TaskResponse(task_id=task_id, status="queued")


@router.post("/video", response_model=TaskResponse)
async def generate_video(
    req: GenerateVideoRequest,
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    current_user: User = Depends(get_current_user),
):
    """Submit a video generation task."""
    return TaskResponse(task_id=str(uuid.uuid4()), status="queued")


@router.get("/tasks/{task_id}", response_model=TaskStatusResponse)
async def get_task_status(
    task_id: str,
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    current_user: User = Depends(get_current_user),
):
    """Check the status of a generation task."""
    from app.services.generation_service import GenerationService

    service = GenerationService()
    status = service.get_task_status(task_id)
    return TaskStatusResponse(
        task_id=task_id,
        status=status.get("status", "unknown"),
        progress=status.get("progress", 0.0),
        result_urls=status.get("result_urls", []),
        error_message=status.get("error_message"),
    )


@router.post("/tasks/{task_id}/cancel")
async def cancel_task(
    task_id: str,
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    current_user: User = Depends(get_current_user),
):
    """Cancel a pending or running generation task."""
    from app.services.generation_service import GenerationService

    service = GenerationService()
    ok = service.cancel_task(task_id)
    return {"task_id": task_id, "status": "cancelled" if ok else "not found"}
