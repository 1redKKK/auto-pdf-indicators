from app.core.nelson import (
    check_rule_2,
    check_rule_3,
    check_rule_4,
    detect_first_match,
)


def test_rule_2_fires_on_run_above_cl():
    cl = 100.0
    values = [110.0] * 9
    assert check_rule_2(values, cl, end_idx=8) is True


def test_rule_2_fires_on_run_below_cl():
    cl = 100.0
    values = [90.0] * 9
    assert check_rule_2(values, cl, end_idx=8) is True


def test_rule_2_does_not_fire_with_mixed_run():
    cl = 100.0
    values = [110.0] * 8 + [90.0]
    assert check_rule_2(values, cl, end_idx=8) is False


def test_rule_2_needs_9_points():
    cl = 100.0
    values = [110.0] * 8
    assert check_rule_2(values, cl, end_idx=7) is False


def test_rule_3_fires_on_increasing_trend():
    values = [1.0, 2.0, 3.0, 4.0, 5.0, 6.0]
    assert check_rule_3(values, end_idx=5) is True


def test_rule_3_fires_on_decreasing_trend():
    values = [10.0, 9.0, 8.0, 7.0, 6.0, 5.0]
    assert check_rule_3(values, end_idx=5) is True


def test_rule_3_rejects_plateau():
    values = [1.0, 2.0, 3.0, 3.0, 4.0, 5.0]
    assert check_rule_3(values, end_idx=5) is False


def test_rule_3_rejects_non_monotonic():
    values = [1.0, 2.0, 3.0, 2.0, 4.0, 5.0]
    assert check_rule_3(values, end_idx=5) is False


def test_rule_4_fires_on_alternation():
    values = [1.0, 2.0, 1.0, 2.0, 1.0, 2.0, 1.0, 2.0, 1.0, 2.0, 1.0, 2.0, 1.0, 2.0]
    assert check_rule_4(values, end_idx=13) is True


def test_rule_4_rejects_two_same_direction():
    values = [1.0, 2.0, 1.0, 2.0, 3.0, 2.0, 1.0, 2.0, 1.0, 2.0, 1.0, 2.0, 1.0, 2.0]
    assert check_rule_4(values, end_idx=13) is False


def test_rule_4_needs_14_points():
    values = [1.0, 2.0, 1.0, 2.0, 1.0, 2.0, 1.0, 2.0, 1.0, 2.0, 1.0, 2.0, 1.0]
    assert check_rule_4(values, end_idx=12) is False


def test_detect_first_match_returns_rule_2_first():
    cl = 100.0
    # Long run above CL — rule 2 should fire before checking trend/alternation
    values = [110.0] * 9
    assert detect_first_match(values, cl, end_idx=8) == "nelson_rule_2"


def test_detect_first_match_returns_none_for_normal_series():
    cl = 100.0
    values = [99.0, 101.0, 100.0, 102.0, 98.0, 100.5]
    assert detect_first_match(values, cl, end_idx=5) is None
