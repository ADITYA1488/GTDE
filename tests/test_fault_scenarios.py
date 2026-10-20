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