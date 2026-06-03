from fastapi import APIRouter, HTTPException, Query

from app.models.heatmap import HeatmapResponse
from app.services.heatmap_service import MAX_LIMIT, DEFAULT_LIMIT, heatmap_service

router = APIRouter()


@router.get("/heatmap", response_model=HeatmapResponse)
def get_heatmap(
    period: str | None = Query(None, pattern=r"^\d{4}-\d{2}$", description="YYYY-MM anchor month"),
    periodicity: str = Query("month", pattern="^(month|quarter|year)$"),
    limit: int = Query(DEFAULT_LIMIT, ge=1, le=MAX_LIMIT),
):
    """Return individual crash coordinates for the chosen window.

    Without `period` — full report period.
    With `period` — that window (`periodicity` controls length).
    Above `limit` points the response is uniformly downsampled.
    """
    try:
        return heatmap_service.get_points(
            period=period,
            periodicity=periodicity,
            limit=limit,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
