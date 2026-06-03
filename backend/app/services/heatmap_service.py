"""Heatmap of crash points for the dashboard map."""

from typing import Optional

from app.core.period_window import resolve_window
from app.core.periods import compute_periods
from app.models.heatmap import HeatmapPoint, HeatmapResponse
from app.services.data_service import data_service


# Soft cap on returned points so the browser doesn't choke on a year's worth.
DEFAULT_LIMIT = 5000
MAX_LIMIT = 20000


class HeatmapService:
    """Return individual crash coordinates over the chosen window."""

    _instance: Optional["HeatmapService"] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def get_points(
        self,
        *,
        period: Optional[str] = None,
        periodicity: str = "month",
        limit: int = DEFAULT_LIMIT,
    ) -> HeatmapResponse:
        df = data_service.get_df()
        if df is None or df.empty:
            return HeatmapResponse(total=0, period_label="", period_months=0, points=[])

        periods = compute_periods(df["datetime"].min(), df["datetime"].max())
        window = resolve_window(
            period,
            periodicity,
            fallback_start=periods["report_start"],
            fallback_end=periods["report_end"],
        )

        sliced = df[
            (df["datetime"] >= window["start"]) & (df["datetime"] < window["end"])
        ]
        total = len(sliced)
        if total > limit:
            # Random sample so points stay representative across the city.
            sliced = sliced.sample(n=limit, random_state=42)

        def _opt(value) -> Optional[str]:
            if value is None:
                return None
            try:
                # pandas/numpy NaN → None
                import math
                if isinstance(value, float) and math.isnan(value):
                    return None
            except Exception:
                pass
            s = str(value).strip()
            return s or None

        points: list[HeatmapPoint] = []
        for _, row in sliced.iterrows():
            sev = str(row["severity"])
            if sev not in ("fatal", "serious", "minor"):
                sev = "minor"
            dt = row["datetime"]
            dt_str = dt.strftime("%Y-%m-%d %H:%M:%S") if hasattr(dt, "strftime") else str(dt)
            points.append(HeatmapPoint(
                lat=round(float(row["lat"]), 6),
                lon=round(float(row["lon"]), 6),
                severity=sev,
                datetime=dt_str,
                address=_opt(row.get("address")),
                district=_opt(row.get("district")),
                crash_type=_opt(row.get("crash_type")),
                dead=int(row.get("dead_count", 0) or 0),
                injured=int(row.get("injured_count", 0) or 0),
            ))

        return HeatmapResponse(
            total=total,
            period_label=window["label"],
            period_months=window["months"],
            points=points,
        )


heatmap_service = HeatmapService()
