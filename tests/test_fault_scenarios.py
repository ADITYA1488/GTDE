from src.demo_network import build_demo_network
from src.restoration import find_restoration_plans


def test_all_single_branch_faults():
    net = build_demo_network()

    faultable = [
        b.branch_id
        for b in net.branches
        if b.normally_closed
    ]

    for fault in faultable:
        plans = find_restoration_plans(
            net,
            faulted_branches={fault},
            max_operations=3,
            max_results=20,
        )

        assert plans, f"No plans returned for {fault}"

        for plan in plans:
            assert fault not in plan.close_ties
            assert fault not in plan.open_branches

        assert any(
            plan.valid for plan in plans
        ), f"No valid plan found for {fault}"



def test_restoration_plan_respects_operation_budget():
    net = build_demo_network()

    # Use an actual normally-closed branch from the demo network.
    faulted_branch = next(
        b.branch_id for b in net.branches if b.normally_closed
    )

    plans = find_restoration_plans(
        net,
        faulted_branches={faulted_branch},
        max_operations=2,
        max_results=20,
    )

    assert plans
    for plan in plans:
        assert plan.switching_operations <= 2
        assert faulted_branch not in plan.close_ties
        assert faulted_branch not in plan.open_branches

def test_restoration_plan_never_switches_faulted_branch():
    net = build_demo_network()

    for branch in net.branches:
        if not branch.normally_closed:
            continue

        plans = find_restoration_plans(
            net,
            faulted_branches={branch.branch_id},
            max_operations=3,
            max_results=20,
        )

        for plan in plans:
            assert branch.branch_id not in plan.close_ties
            assert branch.branch_id not in plan.open_branches


def test_zero_operation_budget_is_supported():
    net = build_demo_network()

    plans = find_restoration_plans(
        net,
        max_operations=0,
        max_results=10,
    )

    assert plans
    assert all(plan.switching_operations == 0 for plan in plans)


def test_invalid_result_limit_returns_empty_list():
    net = build_demo_network()

    assert find_restoration_plans(
        net,
        max_results=0,
    ) == []
