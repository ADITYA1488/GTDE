from src.demo_network import build_demo_network
from src.restoration import find_restoration_plans


from src.demo_network import build_demo_network
def test_total_load():
    assert build_demo_network().total_load_kw() == 540


def test_fault_disconnects_load():
    net = build_demo_network()
    graph = net.build_graph(faulted_branches={"L45"})
    assert net.restored_load_kw(graph) < net.total_load_kw()


def test_tie_restores_all_load():
    net = build_demo_network()
    graph = net.build_graph(
        closed_ties={"T46"},
        faulted_branches={"L45"},
    )
    assert net.restored_load_kw(graph) == 540


def test_cycle_is_rejected():
    net = build_demo_network()
    errors = net.validate_topology(closed_ties={"T46"})
    assert any("cycle" in error.lower() or "radial" in error.lower()
               for error in errors)


def test_search_finds_full_restoration():
    net = build_demo_network()
    plans = find_restoration_plans(
        net, faulted_branches={"L45"},
        max_operations=3, max_results=10,
    )
    assert any(p.valid and p.restored_kw == 540 for p in plans)


def test_faulted_branch_is_not_used():
    net = build_demo_network()
    plans = find_restoration_plans(
        net, faulted_branches={"L45"},
        max_operations=3, max_results=10,
    )
    for plan in plans:
        assert "L45" not in plan.close_ties
        assert "L45" not in plan.open_branches

def test_faulted_branch_cannot_be_switched():
    net = build_demo_network()

    branch = next(
        b for b in net.branches if b.normally_closed
    )

    errors = net.validate_topology(
        opened_branches=[branch.branch_id],
        faulted_branches=[branch.branch_id],
    )

    assert any("faulted" in error for error in errors)


def test_unknown_branch_is_rejected():
    net = build_demo_network()

    errors = net.validate_topology(
        faulted_branches=["UNKNOWN_BRANCH"]
    )

    assert any("Unknown branch ID" in error for error in errors)


def test_non_switchable_tie_cannot_be_closed():
    net = build_demo_network()

    tie = next(
        (
            b for b in net.branches
            if not b.normally_closed
        ),
        None,
    )

    if tie is None:
        return

    # Create a network where this tie cannot be switched.
    from dataclasses import replace
    net.branches = [
        replace(b, switchable=False)
        if b.branch_id == tie.branch_id else b
        for b in net.branches
    ]
    net.branch_by_id = {
        b.branch_id: b for b in net.branches
    }

    errors = net.validate_topology(
        closed_ties=[tie.branch_id]
    )

    assert any("not switchable" in error for error in errors)



def test_restoration_search_retains_only_requested_number_of_plans():
    from src.ieee33_network import build_ieee33_network
    from src.restoration import find_restoration_plans

    plans = find_restoration_plans(
        build_ieee33_network(), faulted_branches={"L10"},
        max_operations=3, max_results=7,
    )
    assert len(plans) == 7
    assert all(plan.valid for plan in plans)
    assert all("L10" not in plan.close_ties for plan in plans)
    assert all("L10" not in plan.open_branches for plan in plans)


def test_restoration_search_rejects_unknown_fault_id():
    import pytest
    from src.ieee33_network import build_ieee33_network
    from src.restoration import find_restoration_plans

    with pytest.raises(ValueError, match="Unknown faulted branch"):
        find_restoration_plans(build_ieee33_network(), {"L99"})
