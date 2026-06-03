from typing import Literal, Optional

from pydantic import BaseModel


HeatmapSeverity = Literal["fatal", "serious", "minor"]


class HeatmapPoint(BaseModel):
    lat: float
    lon: float
    severity: HeatmapSeverity
    datetime: str                   # ISO 'YYYY-MM-DD HH:MM:SS'
    address: Optional[str] = None
    district: Optional[str] = None
    crash_type: Optional[str] = None
    dead: int = 0
    injured: int = 0


class HeatmapResponse(BaseModel):
    total: int
    period_label: str
    period_months: int
    points: list[HeatmapPoint]
