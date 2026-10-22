from src.ieee33_network import build_ieee33_network
from src.restoration_powerflow import evaluate_restoration_plans

net = build_ieee33_network()

for fault in ["L05", "L20"]:
    results = evaluate_restoration_plans(
        net,
        faulted_branches={fault},
        max_operations=4,
        max_results=20,
        capacitor_bus=33,
        capacitor_kvar=1500,
        max_electrical_evaluations=20,
        strategy="baseline",
    )

    feasible = [
        r for r in results
        if r.converged and r.voltage_feasible
        and r.graph_electrical_consistent
        and r.thermal_status != "VIOLATION"
        and r.real_losses_kw is not None
    ]

    print(f"\nFAULT: {fault}; evaluated={len(results)}; feasible={len(feasible)}")
    for r in sorted(feasible, key=lambda x: x.real_losses_kw)[:3]:
        print(
            f"loss={r.real_losses_kw:.3f} kW, "
            f"Vmin={r.min_voltage_pu:.4f}, "
            f"close={r.plan.close_ties}, open={r.plan.open_branches}"
        )
