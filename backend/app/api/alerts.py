from fastapi import APIRouter, HTTPException, Query

from app.models.alerts import AlertAcknowledgeResponse, AlertsResponse
from app.services.alert_service import alert_service

router = APIRouter()


@router.get("/alerts", response_model=AlertsResponse)
def get_alerts(
    status: str = Query("all", pattern="^(new|acknowledged|all)$"),
    level: str = Query("all", pattern="^(critical|warning|info|all)$"),
    limit: int = Query(50, ge=1, le=500),
):
    """Return generated alerts with filters."""
    alerts = alert_service.get_alerts(status=status, level=level, limit=limit)
    return AlertsResponse(total=len(alerts), alerts=alerts)


@router.patch("/alerts/{alert_id}/acknowledge", response_model=AlertAcknowledgeResponse)
def acknowledge_alert(alert_id: str):
    """Set alert status to acknowledged."""
    try:
        return alert_service.acknowledge(alert_id)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Alert not found: {alert_id}")


@router.patch("/alerts/{alert_id}/unacknowledge", response_model=AlertAcknowledgeResponse)
def unacknowledge_alert(alert_id: str):
    """Revert alert status back to new (undo acknowledge)."""
    try:
        return alert_service.unacknowledge(alert_id)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Alert not found: {alert_id}")
