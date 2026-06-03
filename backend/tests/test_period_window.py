import pandas as pd
import pytest

from app.core.period_window import resolve_window


def test_no_period_returns_fallback():
    fallback_start = pd.Timestamp("2025-05-01")
    fallback_end = pd.Timestamp("2026-02-01")
    w = resolve_window(None, "month", fallback_start=fallback_start, fallback_end=fallback_end)
    assert w["start"] == fallback_start
    assert w["end"] == fallback_end
    assert w["months"] == 9


def test_period_month_window():
    w = resolve_window(
        "2025-09",
        "month",
        fallback_start=pd.Timestamp("2024-01-01"),
        fallback_end=pd.Timestamp("2026-01-01"),
    )
    assert w["start"] == pd.Timestamp("2025-09-01")
    assert w["end"] == pd.Timestamp("2025-10-01")
    assert w["months"] == 1


def test_period_quarter_window():
    w = resolve_window(
        "2025-09",
        "quarter",
        fallback_start=pd.Timestamp("2024-01-01"),
        fallback_end=pd.Timestamp("2026-01-01"),
    )
    # Quarter ending at Sep 2025 → Jul..Sep 2025
    assert w["start"] == pd.Timestamp("2025-07-01")
    assert w["end"] == pd.Timestamp("2025-10-01")
    assert w["months"] == 3


def test_period_year_window():
    w = resolve_window(
        "2025-09",
        "year",
        fallback_start=pd.Timestamp("2024-01-01"),
        fallback_end=pd.Timestamp("2026-01-01"),
    )
    # Year ending at Sep 2025 → Oct 2024..Sep 2025
    assert w["start"] == pd.Timestamp("2024-10-01")
    assert w["end"] == pd.Timestamp("2025-10-01")
    assert w["months"] == 12


def test_unknown_periodicity_raises():
    with pytest.raises(ValueError):
        resolve_window("2025-09", "decade", fallback_start=pd.Timestamp("2024-01-01"), fallback_end=pd.Timestamp("2026-01-01"))
