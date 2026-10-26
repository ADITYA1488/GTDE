from types import SimpleNamespace

from dashboard.desktop_app import feasible as desktop_fully_verified
from dashboard.verification import (
    candidate_summary,
    is_fully_verified,
    passes_electrical_checks,
    thermal_unassessed_electrical_candidates,
)


def make_result(
    *, converged=True, voltage=True, graph=True, thermal="UNASSESSED", name="candidate"
):
    return SimpleNamespace(
        converged=converged,
        voltage_feasible=voltage,
        graph_electrical_consistent=graph,
        thermal_status=thermal,
        name=name,
    )


def test_electrical_eligibility_requires_all_three_electrical_checks():
    assert passes_electrical_checks(make_result())
    assert not passes_electrical_checks(make_result(converged=False))
    assert not passes_electrical_checks(make_result(voltage=False))
    assert not passes_electrical_checks(make_result(graph=False))


def test_full_verification_also_requires_thermal_pass():
    assert is_fully_verified(make_result(thermal="PASS"))
    assert not is_fully_verified(make_result(thermal="UNASSESSED"))
    assert not is_fully_verified(make_result(thermal="VIOLATION"))


def test_desktop_fully_verified_rule_matches_shared_rule():
    assert desktop_fully_verified(make_result(thermal="PASS"))
    assert not desktop_fully_verified(make_result(thermal="UNASSESSED"))


def test_thermal_unassessed_metric_only_counts_electrically_eligible_results():
    unassessed = make_result(name="unassessed")
    results = [
        unassessed,
        make_result(name="no convergence", converged=False),
        make_result(name="bad voltage", voltage=False),
        make_result(name="graph mismatch", graph=False),
        make_result(name="thermal pass", thermal="PASS"),
        make_result(name="thermal violation", thermal="VIOLATION"),
    ]

    assert thermal_unassessed_electrical_candidates(results) == [unassessed]


def test_candidate_summary_keeps_result_order_and_marks_fallback_provisional():
    first = make_result(name="first")
    second = make_result(name="second")
    summary = candidate_summary([first, second])

    assert summary["selected"] is first
    assert summary["provisional"] is True
    assert summary["fully_verified"] == []
    assert summary["thermal_unassessed"] == [first, second]


def test_voltage_infeasible_result_is_never_selected_as_recommendation():
    result = make_result(voltage=False)

    summary = candidate_summary([result])

    assert summary["selected"] is None
    assert summary["provisional"] is False
    assert summary["fully_verified"] == []


def test_fully_verified_candidate_is_selected_without_provisional_label():
    unassessed = make_result(name="unassessed")
    verified = make_result(name="verified", thermal="PASS")
    summary = candidate_summary([unassessed, verified])

    assert summary["selected"] is verified
    assert summary["fully_verified"] == [verified]
    assert summary["provisional"] is False
