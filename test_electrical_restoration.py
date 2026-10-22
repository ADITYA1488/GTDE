
from src.ieee33_network import build_ieee33_network
from src.restoration import find_restoration_plans
from src.electrical_restoration import evaluate_restoration_plan


def main():
    net = build_ieee33_network()
    fault = "L10"

    # Generate a larger candidate pool before electrical evaluation.
    plans = find_restoration_plans(
        net,
        faulted_branches={fault},
        max_operations=3,
        max_results=200,
    )

    graph_valid = [p for p in plans if p.valid]
    print(f"Plans returned: {len(plans)}")
    print(f"Graph-valid plans: {len(graph_valid)}")

    evaluated = []

    for plan in graph_valid:
        result = evaluate_restoration_plan(
            plan,
            faulted_branches={fault},
        )
        evaluated.append((plan, result))

    # Rank voltage-feasible candidates first, then by load served,
    # switching operations, and actual OpenDSS real losses.
    evaluated.sort(
        key=lambda item: (
            not item[1]["electrically_feasible"],
            -item[0].restored_kw,
            item[0].switching_operations,
            (
                item[1]["real_losses_kw"]
                if item[1]["real_losses_kw"] is not None
                else float("inf")
            ),
        )
    )

    feasible = [
        (plan, result)
        for plan, result in evaluated
        if result["electrically_feasible"]
    ]

    print(f"Electrically feasible candidates: {len(feasible)}")

    for index, (plan, result) in enumerate(evaluated[:10], start=1):
        print(f"\nCandidate {index}")
        print("Close ties:", plan.close_ties)
        print("Open branches:", plan.open_branches)
        print(f"Graph load served: {plan.restored_kw:.1f} kW")
        print("Power flow converged:", result["powerflow_converged"])
        print("Voltage feasible:", result["voltage_feasible"])
        print("Minimum voltage:", result["min_voltage_pu"])
        print("Maximum voltage:", result["max_voltage_pu"])
        print("Real losses (kW):", result["real_losses_kw"])
        print("Thermal status:", result.get("thermal_status", "UNASSESSED"))


if __name__ == "__main__":
    main()
