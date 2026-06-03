import pytest
import pandas as pd
from app.core.periods import compute_periods


def test_compute_periods_basic():
    """Test compute_periods with standard 21-month dataset."""
    min_date = pd.Timestamp("2024-05-15")
    max_date = pd.Timestamp("2026-01-31")

    result = compute_periods(min_date, max_date)

    assert result["baseline_start"] == pd.Timestamp("2024-05-01")
    assert result["baseline_end"] == pd.Timestamp("2025-05-01")
    assert result["report_start"] == pd.Timestamp("2025-05-01")
    assert result["report_end"] == pd.Timestamp("2026-02-01")
    assert result["baseline_months"] == 12
    assert result["report_months"] == 9


def test_compute_periods_mid_month_end():
    """Test compute_periods when max_date is mid-month (should exclude incomplete month)."""
    min_date = pd.Timestamp("2024-05-01")
    max_date = pd.Timestamp("2026-01-15")

    result = compute_periods(min_date, max_date)

    assert result["baseline_start"] == pd.Timestamp("2024-05-01")
    assert result["baseline_end"] == pd.Timestamp("2025-05-01")
    assert result["report_start"] == pd.Timestamp("2025-05-01")
    assert result["report_end"] == pd.Timestamp("2026-01-01")
    assert result["baseline_months"] == 12
    assert result["report_months"] == 8


def test_compute_periods_exactly_12_months():
    """Test compute_periods when dataset is exactly 12 months."""
    min_date = pd.Timestamp("2024-05-01")
    max_date = pd.Timestamp("2025-05-01")

    result = compute_periods(min_date, max_date)

    assert result["baseline_start"] == pd.Timestamp("2024-05-01")
    assert result["baseline_end"] == pd.Timestamp("2025-05-01")
    assert result["report_start"] == pd.Timestamp("2025-05-01")
    assert result["report_end"] == pd.Timestamp("2025-05-01")
    assert result["baseline_months"] == 12
    assert result["report_months"] == 0
