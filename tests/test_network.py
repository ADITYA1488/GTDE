from src.demo_network import build_demo_network
from src.restoration import find_restoration_plans


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