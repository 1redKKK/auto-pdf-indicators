from typing import Optional

import pandas as pd

from app.config.moscow import MOSCOW_PROFILE
from app.core.period_window import resolve_window
from app.core.periods import compute_periods
from app.models.hotspots import HotspotItem, HotspotsResponse
from app.services.data_service import data_service


class HotspotService:
    """Compute top accident hotspots over a configurable time window."""

    _instance: Optional["HotspotService"] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def get_top(
        self,
        *,
        limit: int = 5,
        period: Optional[str] = None,
        periodicity: str = "month",
    ) -> HotspotsResponse:
        """Return top hotspots for the requested (period, periodicity) window."""
        df = data_service.get_df()
        if df is None or df.empty:
            return HotspotsResponse(hotspots=[], period_label="", period_months=0)

        periods = compute_periods(df["datetime"].min(), df["datetime"].max())
        window = resolve_window(
            period,
            periodicity,
            fallback_start=periods["report_start"],
            fallback_end=periods["report_end"],
        )

        sliced = df[
            (df["datetime"] >= window["start"]) & (df["datetime"] < window["end"])
        ].copy()
        if sliced.empty:
            return HotspotsResponse(
                hotspots=[],
                period_label=window["label"],
                period_months=window["months"],
            )

        sliced["spot_name"] = (
            sliced["address"].fillna(sliced["district"]).fillna("Неизвестный участок")
        )
        grouped = (
            sliced.groupby("spot_name")
            .agg(
                accidents_count=("crash_id", "count"),
                killed=("dead_count", "sum"),
                injured=("injured_count", "sum"),
                lat=("lat", "mean"),
                lon=("lon", "mean"),
                dominant_type=("crash_type", lambda s: (s.dropna().mode().iloc[0]
                                                       if not s.dropna().mode().empty else None)),
            )
            .reset_index()
            .sort_values("accidents_count", ascending=False)
            .head(limit)
            .reset_index(drop=True)
        )

        network_length_km = MOSCOW_PROFILE["network_length_km"]
        hotspots: list[HotspotItem] = []
        for idx, row in grouped.iterrows():
            denominator = row["killed"] + row["injured"]
            # K_T per ВКР 2.3, ×100 для отображения; 0 если killed=0 — это нормально
            severity_coef = (row["killed"] / denominator) * 100 if denominator > 0 else 0.0
            frequency = row["accidents_count"] / window["months"] if window["months"] > 0 else 0.0
            # K_L per ВКР 2.1: вклад этого очага в общую частоту по УДС города
            frequency_per_km = row["accidents_count"] / network_length_km
            status = "active" if row["killed"] > 0 else "potential"

            hotspots.append(
                HotspotItem(
                    rank=idx + 1,
                    name=str(row["spot_name"]),
                    lat=round(float(row["lat"]), 6),
                    lon=round(float(row["lon"]), 6),
                    accidents_count=int(row["accidents_count"]),
                    killed=int(row["killed"]),
                    injured=int(row["injured"]),
                    severity_coef=round(float(severity_coef), 2),
                    frequency=round(float(frequency), 2),
                    frequency_per_km=round(float(frequency_per_km), 4),
                    dominant_type=str(row["dominant_type"]) if row.get("dominant_type") else None,
                    status=status,
                )
            )

        return HotspotsResponse(
            hotspots=hotspots,
            period_label=window["label"],
            period_months=window["months"],
        )


hotspot_service = HotspotService()
