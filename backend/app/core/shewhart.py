import math
from typing import Sequence, Optional


def c_chart_limits(values: Sequence[float]) -> dict:
    """
    Compute C-chart control limits for absolute counts (accidents, killed, injured).

    Args:
        values: Sequence of values for baseline period.

    Returns:
        dict with keys: cl, ucl, lcl (all float).
    """
    if not values:
        return {"cl": 0.0, "ucl": 0.0, "lcl": 0.0}

    mean = sum(values) / len(values)

    if mean == 0:
        return {"cl": 0.0, "ucl": 0.0, "lcl": 0.0}

    sigma = math.sqrt(mean)
    ucl = mean + 3 * sigma
    lcl = max(0.0, mean - 3 * sigma)

    return {"cl": mean, "ucl": ucl, "lcl": lcl}


def u_chart_limits(
    counts: Sequence[float],
    exposures: Optional[Sequence[float]] = None,
    n_const: float = 1.0,
) -> dict:
    """
    Compute U-chart control limits for normalized indicators (severity, social_risk, network_freq).

    Args:
        counts: Sequence of indicator values for baseline period.
        exposures: Unused for simplified version (kept for future extensibility).
        n_const: Fixed exposure for computing limits.

    Returns:
        dict with keys: cl, ucl, lcl (all float).
    """
    if not counts:
        return {"cl": 0.0, "ucl": 0.0, "lcl": 0.0}

    u_bar = sum(counts) / len(counts)

    if u_bar == 0:
        return {"cl": 0.0, "ucl": 0.0, "lcl": 0.0}

    sigma = math.sqrt(u_bar / n_const)
    ucl = u_bar + 3 * sigma
    lcl = max(0.0, u_bar - 3 * sigma)

    return {"cl": u_bar, "ucl": ucl, "lcl": lcl}


def i_chart_limits(values: Sequence[float]) -> dict:
    """
    Compute I-chart (Individuals chart) control limits for ratio/rate indicators.

    Used for indicators that are ratios or rates (severity, social_risk, network_freq),
    where C-chart and U-chart are not applicable.

    Formula:
        CL = mean(values)
        sigma = std(values, ddof=1)  (sample standard deviation)
        UCL = CL + 3*sigma
        LCL = max(0, CL - 3*sigma)

    Args:
        values: Sequence of indicator values for baseline period.

    Returns:
        dict with keys: cl, ucl, lcl (all float).
    """
    if not values or len(values) < 2:
        return {"cl": 0.0, "ucl": 0.0, "lcl": 0.0}

    n = len(values)
    mean = sum(values) / n

    # Sample standard deviation (ddof=1)
    variance = sum((x - mean) ** 2 for x in values) / (n - 1)
    sigma = math.sqrt(variance)

    ucl = mean + 3 * sigma
    lcl = max(0.0, mean - 3 * sigma)

    return {"cl": mean, "ucl": ucl, "lcl": lcl}
