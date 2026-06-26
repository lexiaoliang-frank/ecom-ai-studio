"""Asset management API endpoints."""

import uuid
from typing import Optional

from fastapi import APIRouter, Depends, Query, UploadFile
from pydantic import BaseModel

from app.db.models.user import User
from app.dependencies import get_current_user, get_tenant_id

router = APIRouter()


class AssetResponse(BaseModel):
    id: str
    filename: str
    asset_type: str
    mime_type: Optional[str]
    file_size: Optional[int]
    width: Optional[int]
    height: Optional[int]
    storage_url: Optional[str]
    source_type: Optional[str]
    tags: list[str]
    is_approved: bool
    created_at: str


@router.get("", response_model=list[AssetResponse])
async def list_assets(
    project_id: Optional[str] = Query(None),
    asset_type: Optional[str] = Query(None),
    is_approved: Optional[bool] = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    current_user: User = Depends(get_current_user),
):
    """List assets for the current tenant."""
    # TODO: Implement
    return []


@router.post("/upload")
async def upload_asset(
    file: UploadFile,
    project_id: Optional[str] = None,
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    current_user: User = Depends(get_current_user),
):
    """Upload a product image or reference asset."""
    # TODO: Implement S3/MinIO upload + DB record
    return {"id": str(uuid.uuid4()), "filename": file.filename, "status": "uploaded"}


@router.get("/{asset_id}", response_model=AssetResponse)
async def get_asset(
    asset_id: str,
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    current_user: User = Depends(get_current_user),
):
    """Get a single asset by ID."""
    # TODO: Implement
    raise __import__("fastapi").HTTPException(status_code=404, detail="Asset not found")


@router.delete("/{asset_id}")
async def delete_asset(
    asset_id: str,
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    current_user: User = Depends(get_current_user),
):
    """Delete an asset."""
    return {"id": asset_id, "status": "deleted"}
