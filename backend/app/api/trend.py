from fastapi import APIRouter, HTTPException, Query

from app.core.indicators import CHART_TYPE
from app.models.trend import TrendResponse
from app.services.indicator_service import indicator_service

router = APIRouter()


@router.get("/trend", response_model=TrendResponse)
def get_trend(
    indicator: str = Query(..., description="Код показателя"),
    end_period: str | None = Query(
        None,
        pattern=r"^\d{4}-\d{2}$",
        description="YYYY-MM последний месяц окна; возвращаются 12 точек ending включительно",
    ),
):
    """Get trend data for a single indicator.

    Without `end_period`: cached report-period points (~9 mo).
    With `end_period`: 12 points ending at that month.
    UCL/CL/LCL are baseline-derived in both cases (Shewhart methodology).
    """
    if indicator not in CHART_TYPE:
        raise HTTPException(400, f"Unknown indicator: {indicator}. Allowed: {list(CHART_TYPE)}")
    if not indicator_service.is_ready:
        raise HTTPException(503, "Indicators not ready yet")
    try:
        if end_period is None:
            return indicator_service.get_trend(indicator)
        return indicator_service.get_trend_for_window(indicator, end_period)
    except KeyError:
        raise HTTPException(400, f"Indicator not supported in trend: {indicator}")
    except ValueError as e:
        raise HTTPException(400, str(e))
