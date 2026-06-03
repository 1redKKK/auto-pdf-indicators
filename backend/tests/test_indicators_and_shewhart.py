import pytest
from app.core.indicators import compute_indicator
from app.core.shewhart import c_chart_limits, u_chart_limits
from app.config.moscow import MOSCOW_PROFILE


def test_severity_zero_division():
    """Test severity when both killed and injured are zero."""
    result = compute_indicator(
        "severity",
        n_accidents=0,
        n_killed=0,
        n_injured=0,
        population=MOSCOW_PROFILE["population"],
        network_length_km=MOSCOW_PROFILE["network_length_km"],
        vehicles_count=MOSCOW_PROFILE["vehicles_count"],
    )
    assert result == 0.0


def test_severity_basic():
    """Test severity with 10 killed and 90 injured."""
    result = compute_indicator(
        "severity",
        n_accidents=100,
        n_killed=10,
        n_injured=90,
        population=MOSCOW_PROFILE["population"],
        network_length_km=MOSCOW_PROFILE["network_length_km"],
        vehicles_count=MOSCOW_PROFILE["vehicles_count"],
    )
    assert result == pytest.approx(10.0, rel=1e-6)


def test_social_risk():
    """Test social risk calculation."""
    result = compute_indicator(
        "social_risk",
        n_accidents=0,
        n_killed=131,
        n_injured=0,
        population=13_100_000,
        network_length_km=MOSCOW_PROFILE["network_length_km"],
        vehicles_count=MOSCOW_PROFILE["vehicles_count"],
    )
    assert result == pytest.approx(1.0, rel=1e-3)


def test_network_freq():
    """Test network frequency calculation."""
    result = compute_indicator(
        "network_freq",
        n_accidents=3620,
        n_killed=0,
        n_injured=0,
        population=MOSCOW_PROFILE["population"],
        network_length_km=3620.0,
        vehicles_count=MOSCOW_PROFILE["vehicles_count"],
    )
    assert result == pytest.approx(1.0, rel=1e-6)


def test_transport_risk():
    """Test transport risk calculation."""
    result = compute_indicator(
        "transport_risk",
        n_accidents=0,
        n_killed=408,
        n_injured=0,
        population=MOSCOW_PROFILE["population"],
        network_length_km=MOSCOW_PROFILE["network_length_km"],
        vehicles_count=4_080_000,
    )
    assert result == pytest.approx(1.0, rel=1e-6)


def test_accidents_and_killed_injured():
    """Test basic indicators (accidents, killed, injured)."""
    result_acc = compute_indicator(
        "accidents",
        n_accidents=100,
        n_killed=0,
        n_injured=0,
        population=MOSCOW_PROFILE["population"],
        network_length_km=MOSCOW_PROFILE["network_length_km"],
        vehicles_count=MOSCOW_PROFILE["vehicles_count"],
    )
    assert result_acc == 100.0

    result_killed = compute_indicator(
        "killed",
        n_accidents=0,
        n_killed=50,
        n_injured=0,
        population=MOSCOW_PROFILE["population"],
        network_length_km=MOSCOW_PROFILE["network_length_km"],
        vehicles_count=MOSCOW_PROFILE["vehicles_count"],
    )
    assert result_killed == 50.0

    result_injured = compute_indicator(
        "injured",
        n_accidents=0,
        n_killed=0,
        n_injured=200,
        population=MOSCOW_PROFILE["population"],
        network_length_km=MOSCOW_PROFILE["network_length_km"],
        vehicles_count=MOSCOW_PROFILE["vehicles_count"],
    )
    assert result_injured == 200.0


def test_unknown_indicator():
    """Test that unknown indicator code raises ValueError."""
    with pytest.raises(ValueError):
        compute_indicator(
            "unknown_code",
            n_accidents=0,
            n_killed=0,
            n_injured=0,
            population=MOSCOW_PROFILE["population"],
            network_length_km=MOSCOW_PROFILE["network_length_km"],
            vehicles_count=MOSCOW_PROFILE["vehicles_count"],
        )


def test_c_chart_limits_basic():
    """Test C-chart limits with equal values."""
    values = [100, 100, 100, 100]
    result = c_chart_limits(values)

    assert result["cl"] == pytest.approx(100.0, rel=1e-6)
    assert result["ucl"] == pytest.approx(130.0, rel=1e-6)
    assert result["lcl"] == pytest.approx(70.0, rel=1e-6)


def test_c_chart_limits_lcl_floor():
    """Test that LCL is floored at 0."""
    values = [1, 1, 1, 1]
    result = c_chart_limits(values)

    assert result["cl"] == pytest.approx(1.0, rel=1e-6)
    assert result["lcl"] == 0.0


def test_c_chart_limits_zero_baseline():
    """Test C-chart with all zeros."""
    values = [0, 0, 0]
    result = c_chart_limits(values)

    assert result["cl"] == 0.0
    assert result["ucl"] == 0.0
    assert result["lcl"] == 0.0


def test_c_chart_limits_empty():
    """Test C-chart with empty sequence."""
    result = c_chart_limits([])
    assert result["cl"] == 0.0
    assert result["ucl"] == 0.0
    assert result["lcl"] == 0.0


def test_u_chart_limits_basic():
    """Test U-chart limits with basic values."""
    counts = [10, 10, 10, 10]
    result = u_chart_limits(counts=counts, n_const=100)

    assert result["cl"] == pytest.approx(10.0, rel=1e-6)
    sigma = (10.0 / 100) ** 0.5
    assert result["ucl"] == pytest.approx(10.0 + 3 * sigma, rel=1e-3)
    assert result["lcl"] == pytest.approx(10.0 - 3 * sigma, rel=1e-3)


def test_u_chart_limits_zero_baseline():
    """Test U-chart with all zeros."""
    counts = [0, 0, 0]
    result = u_chart_limits(counts=counts, n_const=100)

    assert result["cl"] == 0.0
    assert result["ucl"] == 0.0
    assert result["lcl"] == 0.0


def test_u_chart_limits_empty():
    """Test U-chart with empty sequence."""
    result = u_chart_limits(counts=[], n_const=100)
    assert result["cl"] == 0.0
    assert result["ucl"] == 0.0
    assert result["lcl"] == 0.0


def test_u_chart_limits_exposures_ignored():
    """Test that exposures parameter is ignored in simplified version."""
    counts = [10, 10, 10, 10]
    exposures = [100, 200, 150, 180]

    result1 = u_chart_limits(counts=counts, exposures=None, n_const=100)
    result2 = u_chart_limits(counts=counts, exposures=exposures, n_const=100)

    assert result1 == result2
