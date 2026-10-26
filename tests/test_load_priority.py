from types import SimpleNamespace

import pytest

from src.network import Branch, DistributionNetwork
from src.restoration import find_restoration_plans
from src.restoration_objectives import restoration_rank


def make_priority_network(
    priority_a=1.0, priority_b=1.0, load_a=100, load_b=100
):
    buses = {
        "source": {"load_kw": 0},
        "a": {"load_kw": load_a, "load_priority_weight": priority_a},
        "b": {"load_kw": load_b, "load_priority_weight": priority_b},
    }
    branches = [
        Branch("fault_a", "source", "a", True),
        Branch("fault_b", "source", "b", True),
        Branch("tie_a", "source", "a", False),
        Branch("tie_b", "source", "b", False),
    ]
    return DistributionNetwork(buses, branches, source_bus="source")


def test_critical_load_weight_can_outweigh_raw_load_in_candidate_selection():
    plans = find_restoration_plans(
        make_priority_network(
            priority_a=5.0, priority_b=1.0, load_a=100, load_b=200
        ),
        faulted_branches={"fault_a", "fault_b"},
        max_operations=1,
        max_results=1,
    )

    assert len(plans) == 1
    assert plans[0].restored_kw == 100
    assert plans[0].close_ties == ["tie_a"]
    assert plans[0].priority_load_score == 500.0


def test_missing_priority_metadata_keeps_equal_priority_score_neutral():
    plan = find_restoration_plans(
        make_priority_network(),
        faulted_branches={"fault_a", "fault_b"},
        max_operations=1,
        max_results=10,
    )[0]

    assert plan.priority_load_score == plan.restored_kw


def test_final_result_ranking_uses_weighted_load_before_raw_load():
    def result(priority_score, restored_kw):
        return SimpleNamespace(
            converged=True,
            voltage_feasible=True,
            graph_electrical_consistent=True,
            thermal_status="PASS",
            real_losses_kw=10.0,
            plan=SimpleNamespace(
                restored_kw=restored_kw,
                priority_load_score=priority_score,
                switching_operations=1,
            ),
        )

    critical_load = result(500.0, 100.0)
    larger_unweighted_load = result(200.0, 200.0)

    assert restoration_rank(critical_load) < restoration_rank(
        larger_unweighted_load
    )


@pytest.mark.parametrize("weight", [-1.0, float("inf"), float("nan")])
def test_invalid_load_priority_weight_is_rejected(weight):
    net = make_priority_network(priority_a=weight)
    with pytest.raises(ValueError, match="load_priority_weight"):
        find_restoration_plans(
            net,
            faulted_branches={"fault_a", "fault_b"},
            max_operations=1,
            max_results=1,
        )
