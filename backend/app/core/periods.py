import pandas as pd
from dateutil.relativedelta import relativedelta


def compute_periods(
    min_date: pd.Timestamp,
    max_date: pd.Timestamp,
    hidden_baseline_months: int = 0,
) -> dict:
    """
    Compute baseline and reporting periods.

    Args:
        min_date: Earliest date in the loaded dataset (may include the hidden
            baseline pool — months loaded only for trailing-12mo baseline calculation).
        max_date: Latest date in the loaded dataset.
        hidden_baseline_months: Leading months reserved as the hidden pool.
            The visible range (baseline + report) starts that many months after `min_date`.

    Returns:
        dict with keys: data_start, baseline_start, baseline_end, report_start, report_end,
        baseline_months, report_months.
        _start/_end are pd.Timestamp at the 1st of month; _end is exclusive.
        `data_start` = beginning of the loaded data (includes hidden pool).
        `baseline_start` = beginning of the visible range.
    """
    data_start = pd.Timestamp(year=min_date.year, month=min_date.month, day=1)
    visible_start = data_start + relativedelta(months=hidden_baseline_months)

    baseline_start = visible_start
    baseline_end = baseline_start + relativedelta(months=12)

    report_start = baseline_end

    if max_date.day >= 28:
        report_end = pd.Timestamp(year=max_date.year, month=max_date.month, day=1) + relativedelta(months=1)
    else:
        report_end = pd.Timestamp(year=max_date.year, month=max_date.month, day=1)

    baseline_months = 12
    report_months = 0
    current = report_start
    while current < report_end:
        report_months += 1
        current = current + relativedelta(months=1)

    return {
        "data_start": data_start,
        "baseline_start": baseline_start,
        "baseline_end": baseline_end,
        "report_start": report_start,
        "report_end": report_end,
        "baseline_months": baseline_months,
        "report_months": report_months,
    }
