from src.demo_network import build_demo_network
from src.restoration import find_restoration_plans


def main():
    net = build_demo_network()
    faulted = {"L45"}
    graph = net.build_graph(faulted_branches=faulted)

    print("GraD — Feeder Restoration Engine")
    print("=" * 40)
    print("Faulted branch:", ", ".join(sorted(faulted)))
    print("Initially supplied buses:", sorted(net.supplied_buses(graph)))
    print(
        f"Initially restored: {net.restored_load_kw(graph):.1f} / "
        f"{net.total_load_kw():.1f} kW"
    )

    plans = find_restoration_plans(
        net, faulted_branches=faulted,
        max_operations=3, max_results=10
    )

    print("\nCandidate plans:")
    for i, plan in enumerate(plans, 1):
        print(
            f"{i}. close={plan.close_ties or '-'} "
            f"open={plan.open_branches or '-'} | "
            f"restored={plan.restored_kw:.1f} kW "
            f"({plan.restoration_pct:.1f}%) | "
            f"operations={plan.switching_operations} | "
            f"valid={plan.valid} | "
            f"graph_proxy={plan.estimated_loss_kw:.5f}"
        )


if __name__ == "__main__":
    main()