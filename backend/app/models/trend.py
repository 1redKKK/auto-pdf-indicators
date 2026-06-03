from pydantic import BaseModel, Field
from typing import Optional, Literal


class TrendPoint(BaseModel):
    date: str  # "YYYY-MM-01"
    month_label: str  # "Май 2025"
    value: float
    out_of_control: bool
    alert_level: Optional[Literal["critical", "warning", "info"]] = None


class TrendResponse(BaseModel):
    indicator: str  # "accidents"
    label: str  # "Число ДТП"
    unit: str
    chart_type: Literal["c-chart", "u-chart", "i-chart"]
    cl: float
    ucl: float
    lcl: float
    points: list[TrendPoint]
    baseline_months: int  # 12
    report_months: int  # ~9
