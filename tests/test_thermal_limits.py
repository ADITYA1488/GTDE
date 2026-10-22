import pytest

from src.thermal_limits import (
    check_branch_ampacity,
    check_feeder_ampacity,
    feeder_thermal_status,
)


def test_branch_within_ampacity_passes():
    result = check_branch_ampacity("L01", 80.0, 100.0)

    assert result.status == "PASS"
    assert result.margin_a == pytest.approx(20.0)
    assert result.loading_pct == pytest.approx(80.0)


def test_branch_over_ampacity_fails():
    result = check_branch_ampacity("L01", 105.0, 100.0)

    assert result.status == "VIOLATION"
    assert result.margin_a == pytest.approx(-5.0)


def test_missing_rating_is_unassessed():
    result = check_branch_ampacity("L01", 80.0, None)

    assert result.status == "UNASSESSED"
    assert result.loading_pct is None


def test_invalid_ampacity_is_rejected():
    with pytest.raises(ValueError):
        check_branch_ampacity("L01", 80.0, 0.0)


def test_feeder_does_not_hide_missing_ratings():
    results = check_feeder_ampacity(
        branch_currents_a={"L01": 80.0, "L02": 40.0},
        ampacity_ratings_a={"L01": 100.0},
    )

    assert results[0].status == "PASS"
    assert results[1].status == "UNASSESSED"
    assert feeder_thermal_status(results) == "UNASSESSED"


def test_feeder_violation_takes_priority():
    results = check_feeder_ampacity(
        branch_currents_a={"L01": 105.0, "L02": 40.0},
        ampacity_ratings_a={"L01": 100.0},
    )

    assert feeder_thermal_status(results) == "VIOLATION"