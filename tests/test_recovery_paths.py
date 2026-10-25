from types import SimpleNamespace

from src.network import Branch, DistributionNetwork
from src.restoration import (
    _candidate_rank_key,
    _candidate_state,
    _recovery_path_context,
    find_restoration_plans,
)


def make_multifault_network():
    buses = {
        bus: {"load_kw": load}
        for bus, load in {
            "source": 0,
            "north": 10,
            "junction": 20,
            "outage_a": 30,
            "outage_b": 40,
            "outage_c": 50,
            "outage_d": 60,
        }.items()
    }
    branches = [
        Branch("feeder_north", "source", "north", True),
        Branch("feeder_junction", "north", "junction", True),
        Branch("fault_one", "junction", "outage_a", True),
        Branch("outage_link", "outage_a", "outage_b", True),
        Branch("fault_two", "outage_b", "outage_c", True),
        Branch("outage_tail", "outage_c", "outage_d", True),
        Branch("tie_left", "north", "outage_a", False),
        Branch("tie_right", "junction", "outage_c", False),
        Branch("tie_inside_outage", "outage_a", "outage_d", False),
        Branch("tie_inside_source", "source", "junction", False),
    ]
    return DistributionNetwork(buses, branches, source_bus="source")


def test_outage_region_and_boundary_ties_follow_fault_cut_components():
    net = make_multifault_network()

    outage_buses, boundary_ties, _ = _recovery_path_context(
        net, {"fault_one", "fault_two"}
    )

    assert outage_buses == {"outage_a", "outage_b", "outage_c", "outage_d"}
    assert set(boundary_ties) == {"tie_left", "tie_right"}
    assert "tie_inside_outage" not in boundary_ties
    assert "tie_inside_source" not in boundary_ties


def test_multiple_faults_are_removed_together_and_keep_components_separate():
    net = make_multifault_network()

    outage_buses, boundary_ties, _ = _recovery_path_context(
        net, {"fault_one", "fault_two"}
    )

    # fault_one leaves two outage components when fault_two is also removed.
    assert {"outage_a", "outage_b"} <= outage_buses
    assert {"outage_c", "outage_d"} <= outage_buses
    assert set(boundary_ties) == {"tie_left", "tie_right"}


def test_source_paths_use_active_branch_routes_to_each_boundary_tie():
    net = make_multifault_network()

    _, _, source_paths = _recovery_path_context(
        net, {"fault_one", "fault_two"}
    )

    assert source_paths == {
        "tie_left": ("feeder_north",),
        "tie_right": ("feeder_north", "feeder_junction"),
    }


def test_boundary_tie_closure_preserves_radiality_and_joint_cycle_is_rejected():
    net = make_multifault_network()
    faulted = {"fault_one", "fault_two"}

    valid, _, supplied, _ = _candidate_state(
        net, {"tie_left"}, set(), faulted
    )
    assert valid
    assert "outage_a" in supplied

    # The two boundary ties plus the tie wholly inside the outage region form
    # a cycle after the fault cuts are applied.
    valid, errors, _, _ = _candidate_state(
        net,
        {"tie_left", "tie_right", "tie_inside_outage"},
        set(),
        faulted,
    )
    assert not valid
    assert any("cycle" in error.lower() for error in errors)


def test_recovery_path_priority_breaks_only_equal_load_and_operation_ties():
    relevant = SimpleNamespace(
        restored_kw=100.0,
        switching_operations=2,
        estimated_loss_kw=50.0,
        close_ties=["boundary_tie"],
        open_branches=[],
        valid=True,
    )
    irrelevant_but_lower_loss = SimpleNamespace(
        restored_kw=100.0,
        switching_operations=2,
        estimated_loss_kw=1.0,
        close_ties=["other_tie"],
        open_branches=[],
        valid=True,
    )
    higher_load_irrelevant = SimpleNamespace(
        restored_kw=101.0,
        switching_operations=3,
        estimated_loss_kw=100.0,
        close_ties=["other_tie"],
        open_branches=[],
        valid=True,
    )
    fewer_operations_irrelevant = SimpleNamespace(
        restored_kw=100.0,
        switching_operations=1,
        estimated_loss_kw=100.0,
        close_ties=["other_tie"],
        open_branches=[],
        valid=True,
    )

    source_paths = {"boundary_tie": ("source_line",)}
    relevant_key = _candidate_rank_key(relevant, source_paths)
    assert relevant_key > _candidate_rank_key(
        irrelevant_but_lower_loss, source_paths
    )
    assert _candidate_rank_key(
        higher_load_irrelevant, source_paths
    ) > relevant_key
    assert _candidate_rank_key(
        fewer_operations_irrelevant, source_paths
    ) > relevant_key

    path_cut = SimpleNamespace(
        restored_kw=100.0,
        switching_operations=2,
        estimated_loss_kw=1.0,
        close_ties=["boundary_tie"],
        open_branches=["source_line"],
        valid=True,
    )
    assert _candidate_rank_key(path_cut, source_paths)[2] == 0


def test_candidates_without_recovery_path_ties_remain_in_search_alternatives():
    net = make_multifault_network()

    plans = find_restoration_plans(
        net,
        faulted_branches={"fault_one", "fault_two"},
        max_operations=1,
        max_results=100,
    )

    assert any(
        plan.valid
        and not plan.close_ties
        and plan.open_branches == ["feeder_north"]
        for plan in plans
    )
