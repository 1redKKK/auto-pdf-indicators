from fastapi import APIRouter, HTTPException, Query

from app.models.indicators import IndicatorsResponse
from app.services.alert_service import alert_service
from app.services.indicator_service import indicator_service

router = APIRouter()


@router.get("/indicators", response_model=IndicatorsResponse)
def get_indicators(
    period: str | None = Query(None, pattern=r"^\d{4}-\d{2}$", description="YYYY-MM anchor month"),
    periodicity: str = Query("month", pattern="^(month|quarter|year)$"),
):
    """Return KPI cards.

    Without `period`: returns the cached values for the full report period.
    With `period`: recomputes KPI for the requested window; baseline is the
    same-length window shifted 12 months earlier (year-over-year comparison).
    """
    if not indicator_service.is_ready:
        raise HTTPException(503, "Indicators not ready yet")

    if period is None:
        return indicator_service.get_indicators()

    try:
        return indicator_service.get_indicators_for_window(period=period, periodicity=periodicity)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/indicators/calculate", response_model=IndicatorsResponse)
def recalculate_indicators():
    """Recalculate indicators."""
    try:
        indicator_service.recompute()
        alert_service.recompute()
    except RuntimeError as e:
        raise HTTPException(503, str(e))
    return indicator_service.get_indicators()
