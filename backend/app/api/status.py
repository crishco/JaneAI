"""Runtime status API routes."""

import logging

from fastapi import APIRouter, Request

from app.core.status import status_manager
from app.models.status import StatusResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/status", tags=["status"])


@router.get("", response_model=StatusResponse)
async def get_status(request: Request) -> StatusResponse:
    """Return the current agent activity and startup/runtime errors."""
    snapshot = status_manager.snapshot()
    startup_errors = getattr(request.app.state, "startup_errors", [])
    backend_healthy = len(startup_errors) == 0

    if startup_errors and not snapshot.errors:
        for error in startup_errors:
            status_manager.add_error(error)
        snapshot = status_manager.snapshot()

    return StatusResponse(
        status=snapshot.status,
        detail=snapshot.detail,
        errors=snapshot.errors,
        updated_at=snapshot.updated_at,
        backend_healthy=backend_healthy,
    )
