from fastapi import APIRouter, Depends, Query

from src.schemas import Page
from src.auth.dependencies import require_admin
from src.activity.schema import ActivityEvent
from src.activity.service import ActivityService, get_activity_service

# Audit data is sensitive → admin-only (reuses the RBAC gate from §19).
router = APIRouter(prefix="/activity", tags=["activity"], dependencies=[Depends(require_admin)])


@router.get("", response_model=Page[ActivityEvent])
async def list_activity(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    service: ActivityService = Depends(get_activity_service),
):
    """Recent activity events from MongoDB, newest first."""
    items, total = await service.list_recent(limit=limit, offset=offset)
    return Page(items=items, total=total, limit=limit, offset=offset)
