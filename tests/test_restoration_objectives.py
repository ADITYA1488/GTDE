
from types import SimpleNamespace

from src.restoration_objectives import restoration_rank


def make_result(
    feasible, restored, operations, losses, *, graph=True, thermal="PASS"
):
    plan = SimpleNamespace(
        restored_kw=restored,
        switching_operations=operations,
    )
    return SimpleNamespace(
        converged=feasible,
        voltage_feasible=feasible,
        graph_electrical_consistent=graph,
        thermal_status=thermal,
        plan=plan,
        real_losses_kw=losses,
    )


def test_feasible_candidate_beats_infeasible_candidate():
    good = make_result(True, 500, 2, 20)
    bad = make_result(False, 700, 1, 10)

    assert restoration_rank(good) < restoration_rank(bad)


def test_graph_inconsistency_fails_ranking_feasibility_gate():
    consistent = make_result(True, 500, 2, 20)
    inconsistent = make_result(True, 700, 1, 10, graph=False)

    assert restoration_rank(consistent) < restoration_rank(inconsistent)


def test_unassessed_thermal_status_fails_ranking_feasibility_gate():
    thermal_pass = make_result(True, 500, 2, 20)
    thermal_unassessed = make_result(
        True, 700, 1, 10, thermal="UNASSESSED"
    )

    assert restoration_rank(thermal_pass) < restoration_rank(thermal_unassessed)


def test_more_restored_load_has_priority():
    a = make_result(True, 600, 3, 40)
    b = make_result(True, 500, 1, 10)

    assert restoration_rank(a) < restoration_rank(b)


def test_lower_losses_take_priority_over_fewer_operations():
    lower_losses = make_result(True, 500, 3, 10)
    fewer_operations = make_result(True, 500, 1, 20)

    assert restoration_rank(lower_losses) < restoration_rank(fewer_operations)


def test_fewer_operations_break_remaining_tie():
    fewer_operations = make_result(True, 500, 1, 20)
    more_operations = make_result(True, 500, 2, 20)

    assert restoration_rank(fewer_operations) < restoration_rank(more_operations)


def test_missing_losses_rank_after_measured_losses():
    measured = make_result(True, 500, 4, 100)
    missing = make_result(True, 500, 1, None)

    assert restoration_rank(measured) < restoration_rank(missing)
