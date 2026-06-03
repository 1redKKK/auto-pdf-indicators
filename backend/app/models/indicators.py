from pydantic import BaseModel, Field
from typing import Optional, Literal


class IndicatorCard(BaseModel):
    code: str
    label: str
    unit: str
    value: float
    delta_abs: Optional[float] = None
    delta_pct: Optional[float] = None
    is_improvement: Optional[bool] = None


class PeriodInfo(BaseModel):
    baseline_start: str
    baseline_end: str
    report_start: str
    report_end: str
    baseline_months: int
    report_months: int


class IndicatorsResponse(BaseModel):
    region: str = "Москва"
    period: PeriodInfo
    last_calculated_at: str
    cards: list[IndicatorCard]
