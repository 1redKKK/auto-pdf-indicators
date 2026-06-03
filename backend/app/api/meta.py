import pandas as pd
from fastapi import APIRouter, HTTPException

from app.config.settings import settings
from app.core.periods import compute_periods
from app.services.data_service import data_service


router = APIRouter()


@router.get("/meta")
def get_meta():
    """Return metadata. `available_periods` lists only the visible months;
    the hidden trailing-baseline pool is not user-selectable."""
    if data_service.df is None or len(data_service.df) == 0:
        raise HTTPException(status_code=503, detail="Data not loaded")

    base_meta = data_service.get_meta()

    df = data_service.df
    periods = compute_periods(
        df["datetime"].min(),
        df["datetime"].max(),
        hidden_baseline_months=settings.HIDDEN_BASELINE_MONTHS,
    )
    visible_start = periods["baseline_start"]
    months = sorted(
        m for m in df["year_month"].unique().tolist()
        if pd.Timestamp(m + "-01") >= visible_start
    )

    base_meta["period"] = {
        "baseline_start": periods["baseline_start"].strftime("%Y-%m-%d"),
        "baseline_end": periods["baseline_end"].strftime("%Y-%m-%d"),
        "report_start": periods["report_start"].strftime("%Y-%m-%d"),
        "report_end": periods["report_end"].strftime("%Y-%m-%d"),
        "baseline_months": periods["baseline_months"],
        "report_months": periods["report_months"],
    }
    base_meta["available_periods"] = months

    return base_meta
