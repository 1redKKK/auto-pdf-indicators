import pandas as pd
import pytest
from app.services.indicator_service import IndicatorService


@pytest.fixture
def synthetic_df():
    """36 months: 12 hidden baseline pool + 12 visible baseline + 12 visible report."""
    rows = []
    for year in [2023, 2024, 2025]:
        for month in range(1, 13):
            for i in range(100):
                rows.append({
                    "crash_id": f"{year}-{month:02d}-{i}",
                    "datetime": pd.Timestamp(year=year, month=month, day=15),
                    "year": year,
                    "month": month,
                    "lat": 55.75,
                    "lon": 37.62,
                    "dead_count": 1 if i < 5 else 0,
                    "injured_count": 1 if i < 50 else 0,
                    "severity": "minor",
                    "severity_raw": "Лёгкий",
                    "district": "Центр",
                    "crash_type": "столкновение",
                    "road_condition": None,
                    "address": "Main Street",
                    "year_month": f"{year}-{month:02d}",
                })
    return pd.DataFrame(rows)


def test_recompute_basic(monkeypatch, synthetic_df):
    from app.services import data_service as ds_mod
    monkeypatch.setattr(ds_mod.data_service, "get_df", lambda: synthetic_df)

    svc = IndicatorService()
    svc.recompute()

    assert svc.is_ready
    resp = svc.get_indicators()
    assert resp.region == "Москва"
    assert len(resp.cards) == 4
    codes = [c.code for c in resp.cards]
    assert codes == ["accidents", "severity", "social_risk", "network_freq"]


def test_trend_returns_correct_count(monkeypatch, synthetic_df):
    from app.services import data_service as ds_mod
    monkeypatch.setattr(ds_mod.data_service, "get_df", lambda: synthetic_df)

    svc = IndicatorService()
    svc.recompute()
    trend = svc.get_trend("accidents")
    assert trend.chart_type == "c-chart"
    assert trend.baseline_months == 12
    # For synthetic 2024-2025, report period is around 12 months
    assert trend.report_months >= 1
    assert len(trend.points) == trend.report_months


def test_unknown_indicator_raises(monkeypatch, synthetic_df):
    from app.services import data_service as ds_mod
    monkeypatch.setattr(ds_mod.data_service, "get_df", lambda: synthetic_df)

    svc = IndicatorService()
    svc.recompute()
    with pytest.raises(KeyError):
        svc.get_trend("nonexistent")
