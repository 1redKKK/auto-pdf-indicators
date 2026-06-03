from typing import Literal, Optional

from pydantic import BaseModel


HotspotStatus = Literal["active", "potential"]


class HotspotItem(BaseModel):
    rank: int
    name: str
    lat: float
    lon: float
    accidents_count: int
    killed: int
    injured: int
    severity_coef: float            # K_T per ВКР 2.3 (×100), 0 if killed=0
    frequency: float                # ДТП/мес (accidents_count / period_months)
    frequency_per_km: float         # K_L per ВКР 2.1 (accidents_count / L_сети, ДТП/км)
    dominant_type: Optional[str] = None    # преобладающий тип ДТП в очаге
    status: HotspotStatus           # active = killed > 0 in window, else potential


class HotspotsResponse(BaseModel):
    hotspots: list[HotspotItem]
    period_label: str           # human-readable window label
    period_months: int          # how many months the window covers
