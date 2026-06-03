from pydantic import BaseModel
from typing import Literal


AlertLevel = Literal["critical", "warning", "info"]
AlertStatus = Literal["new", "acknowledged"]
AlertType = Literal["A", "B", "C"]


class AlertItem(BaseModel):
    id: str
    datetime: str
    region: str
    indicator: str
    indicator_label: str
    rule: str
    rule_label: str
    level: AlertLevel
    level_label: str
    type: AlertType
    value: float
    threshold: float
    status: AlertStatus
    description: str


class AlertsResponse(BaseModel):
    total: int
    alerts: list[AlertItem]


class AlertAcknowledgeResponse(BaseModel):
    id: str
    status: AlertStatus
    acknowledged_at: str
