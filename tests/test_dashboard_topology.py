from src.ieee33_network import build_ieee33_network
from src.restoration import find_restoration_plans
from dashboard.topology import (
    VIEWS,
    build_feeder_figure,
    candidate_label,
    select_candidate,
    supported_faults,
    topology_state,
)


def test_scenario_choices_are_supported_normally_closed_branches():
    net = build_ieee33_network()
    actual = {b.branch_id for b in net.branches if b.normally_closed}
    assert supported_faults(net) == ["L05", "L10", "L15", "L20", "L25", "L30"]
    assert set(supported_faults(net)) <= actual


def test_all_views_use_actual_model_branch_endpoints_and_all_33_buses():
    net = build_ieee33_network()
    expected = {b.branch_id: (b.u, b.v) for b in net.branches}

    for view in VIEWS:
        state = topology_state(net, {"L10"}, view=view)
        assert len(state["branches"]) == len(net.branches) == 37
        assert {row["branch_id"] for row in state["branches"]} == set(expected)
        assert all((row["u"], row["v"]) == expected[row["branch_id"]] for row in state["branches"])
        figure = build_feeder_figure(net, {"L10"}, view=view)
        assert len(figure.data) == len(net.branches) + 1
        assert len(figure.data[-1].x) == 33

    pre = topology_state(net, {"L10"}, view="Pre-fault")
    post = topology_state(net, {"L10"}, view="Post-fault")
    assert len(pre["supplied_buses"]) == 33
    assert 11 not in post["supplied_buses"]
    assert "L10" in {row["branch_id"] for row in post["branches"] if row["state"] == "faulted"}
    assert any(row["state"] == "de-energized segment" for row in post["branches"])


def test_candidate_state_highlights_only_active_model_recovery_path():
    net = build_ieee33_network()
    plan = next(
        plan for plan in find_restoration_plans(net, {"L10"}, 3, 100)
        if plan.valid and plan.restored_kw > 0
    )
    state = topology_state(net, {"L10"}, plan, "Candidate restoration")
    rows = {row["branch_id"]: row for row in state["branches"]}
    assert rows["L10"]["state"] == "faulted"
    assert state["recovery_path_branches"] <= {
        row["branch_id"] for row in state["branches"] if row["active"]
    }
    assert all(rows[branch_id]["path"] for branch_id in state["recovery_path_branches"])


def test_candidate_selection_matches_labelled_index_and_rejects_bad_index():
    net = build_ieee33_network()
    plans = find_restoration_plans(net, {"L10"}, 3, 2)
    candidates = [type("Result", (), {"plan": plan})() for plan in plans]
    assert select_candidate(candidates, 1) is candidates[1]
    assert candidate_label(0, candidates[0]).startswith("Candidate 1 ·")
    assert select_candidate([], 0) is None
    try:
        select_candidate(candidates, len(candidates))
    except IndexError:
        pass
    else:
        raise AssertionError("out-of-range candidate must fail")
