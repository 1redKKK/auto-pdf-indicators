from typing import Literal

from pydantic import BaseModel


ReportPeriodicity = Literal["month", "quarter", "year"]


class ReportItem(BaseModel):
    id: str                       # rpt_001, rpt_002, …
    title: str                    # «Аналитический отчёт за Декабрь 2025»
    region: str                   # "moscow"
    region_label: str             # "Москва"
    period: str                   # YYYY-MM anchor
    periodicity: ReportPeriodicity
    period_label: str             # "Декабрь 2025"
    generated_at: str             # ISO datetime
    file_name: str                # "BDD_Moscow_Dec_2025.pdf"
    size_bytes: int


class ReportsResponse(BaseModel):
    total: int
    reports: list[ReportItem]


class ReportGenerateRequest(BaseModel):
    region: str = "moscow"
    period: str                   # YYYY-MM (required)
    periodicity: ReportPeriodicity = "month"
