from fastapi import APIRouter, HTTPException, Query

from app.models.hotspots import HotspotsResponse
from app.services.hotspot_service import hotspot_service

router = APIRouter()


@router.get("/hotspots/top", response_model=HotspotsResponse)
def get_top_hotspots(
    limit: int = Query(5, ge=1, le=20),
    period: str | None = Query(None, pattern=r"^\d{4}-\d{2}$", description="YYYY-MM anchor month"),
    periodicity: str = Query("month", pattern="^(month|quarter|year)$"),
):
    """Return top accident hotspots for the dashboard.

    Without `period`: aggregates over the full report period.
    With `period`: aggregates over the window ending at that month, sized by `periodicity`.
    """
    try:
        return hotspot_service.get_top(limit=limit, period=period, periodicity=periodicity)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
