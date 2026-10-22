
from src.thermal_limits import check_branch_ampacity, feeder_thermal_status


def test_branch_below_ampacity_passes():
    result = check_branch_ampacity(
        branch_id="L01",
        measured_current_a=150.0,
        ampacity_a=200.0,
    )
    assert result.status == "PASS"
    assert result.margin_a == 50.0


def test_branch_above_ampacity_violates():
    result = check_branch_ampacity(
        branch_id="L01",
        measured_current_a=220.0,
        ampacity_a=200.0,
    )
    assert result.status == "VIOLATION"


def test_missing_ampacity_is_unassessed():
    result = check_branch_ampacity(
        branch_id="L01",
        measured_current_a=150.0,
        ampacity_a=None,
    )
    assert result.status == "UNASSESSED"


def test_feeder_violation_takes_priority():
    results = [
        check_branch_ampacity("L01", 150.0, 200.0),
        check_branch_ampacity("L02", 220.0, 200.0),
        check_branch_ampacity("L03", 50.0, None),
    ]
    assert feeder_thermal_status(results) == "VIOLATION"


def test_feeder_with_missing_rating_is_unassessed():
    results = [
        check_branch_ampacity("L01", 150.0, 200.0),
        check_branch_ampacity("L02", 50.0, None),
    ]
    assert feeder_thermal_status(results) == "UNASSESSED"
