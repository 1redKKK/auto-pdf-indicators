"""Resolve (period, periodicity) query params into a [start, end) date window.

Used by /hotspots/top and /indicators to slice data per UI selector.
"""

from typing import Optional

import pandas as pd
from dateutil.relativedelta import relativedelta


PERIODICITY_MONTHS = {"month": 1, "quarter": 3, "year": 12}


def resolve_window(
    period: Optional[str],
    periodicity: str,
    *,
    fallback_start: pd.Timestamp,
    fallback_end: pd.Timestamp,
) -> dict:
    """Convert a (period, periodicity) selection into an inclusive month range.

    Args:
        period: "YYYY-MM" anchor month, or None to use the full fallback range.
        periodicity: One of "month" | "quarter" | "year".
        fallback_start: Used when period is None (e.g. report_start).
        fallback_end: Used when period is None (e.g. report_end, exclusive).

    Returns:
        dict with keys: start (Timestamp, inclusive), end (Timestamp, exclusive),
        months (int), label (str).
    """
    if periodicity not in PERIODICITY_MONTHS:
        raise ValueError(f"Unknown periodicity: {periodicity}")

    if period is None:
        # No anchor: use the supplied fallback range untouched.
        months = _count_months(fallback_start, fallback_end)
        return {
            "start": fallback_start,
            "end": fallback_end,
            "months": months,
            "label": _range_label(fallback_start, fallback_end),
        }

    anchor = pd.Timestamp(period + "-01")
    months = PERIODICITY_MONTHS[periodicity]
    end = anchor + relativedelta(months=1)
    start = end - relativedelta(months=months)

    return {
        "start": start,
        "end": end,
        "months": months,
        "label": _range_label(start, end),
    }


def _count_months(start: pd.Timestamp, end: pd.Timestamp) -> int:
    months = 0
    current = start
    while current < end:
        months += 1
        current = current + relativedelta(months=1)
    return months


_RU_MONTHS_SHORT = [
    "Янв", "Фев", "Мар", "Апр", "Май", "Июн",
    "Июл", "Авг", "Сен", "Окт", "Ноя", "Дек",
]


def _range_label(start: pd.Timestamp, end: pd.Timestamp) -> str:
    last = end - relativedelta(months=1)
    if start.year == last.year and start.month == last.month:
        return f"{_RU_MONTHS_SHORT[start.month - 1]} {start.year}"
    return (
        f"{_RU_MONTHS_SHORT[start.month - 1]} {start.year} — "
        f"{_RU_MONTHS_SHORT[last.month - 1]} {last.year}"
    )
