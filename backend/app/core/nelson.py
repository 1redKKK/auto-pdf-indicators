"""Nelson rules 2, 3, 4 for control chart anomaly detection.

Per ВКР раздел 2.2.3:
- Rule 2: 9 consecutive points on one side of CL (systematic shift) — WARNING type B
- Rule 3: 6 consecutive monotonic points (trend) — WARNING type B
- Rule 4: 14 consecutive alternating points (oscillation) — WARNING type B

Each function checks whether the rule fires AT a given index, looking back into the series.
"""

from typing import Sequence


def check_rule_2(values: Sequence[float], cl: float, end_idx: int, run_length: int = 9) -> bool:
    """Return True if 9 consecutive points ending at end_idx are on one side of CL."""
    if end_idx + 1 < run_length:
        return False
    window = values[end_idx - run_length + 1 : end_idx + 1]
    above = all(v > cl for v in window)
    below = all(v < cl for v in window)
    return above or below


def check_rule_3(values: Sequence[float], end_idx: int, trend_length: int = 6) -> bool:
    """Return True if 6 consecutive points ending at end_idx form a monotonic trend."""
    if end_idx + 1 < trend_length:
        return False
    window = values[end_idx - trend_length + 1 : end_idx + 1]
    increasing = all(window[i] > window[i - 1] for i in range(1, len(window)))
    decreasing = all(window[i] < window[i - 1] for i in range(1, len(window)))
    return increasing or decreasing


def check_rule_4(values: Sequence[float], end_idx: int, alt_length: int = 14) -> bool:
    """Return True if 14 consecutive points ending at end_idx alternate up/down."""
    if end_idx + 1 < alt_length:
        return False
    window = values[end_idx - alt_length + 1 : end_idx + 1]
    diffs = [window[i] - window[i - 1] for i in range(1, len(window))]
    if any(d == 0 for d in diffs):
        return False
    signs = [d > 0 for d in diffs]
    for i in range(1, len(signs)):
        if signs[i] == signs[i - 1]:
            return False
    return True


def detect_first_match(values: Sequence[float], cl: float, end_idx: int) -> str | None:
    """Check rules 2, 3, 4 in order; return first matching rule code or None.

    Rule precedence: rule_2 > rule_3 > rule_4 (most specific systematic pattern wins).
    """
    if check_rule_2(values, cl, end_idx):
        return "nelson_rule_2"
    if check_rule_3(values, end_idx):
        return "nelson_rule_3"
    if check_rule_4(values, end_idx):
        return "nelson_rule_4"
    return None
