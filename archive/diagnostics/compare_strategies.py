from src.ieee33_network import build_ieee33_network
from src.restoration_powerflow import evaluate_restoration_plans

net = build_ieee33_network()

common = dict(
    faulted_branches={"L10"},
    max_operations=3,
    max_results=10,
    capacitor_bus=33,
    capacitor_kvar=900,
    max_electrical_evaluations=10,
)

for strategy in ("baseline", "adaptive"):
    results = evaluate_restoration_plans(
        net, **common, strategy=strategy
    )

    feasible = [
        r for r in results
        if r.converged
        and r.voltage_feasible
        and r.graph_electrical_consistent
        and r.thermal_status != "VIOLATION"
        and r.real_losses_kw is not None
    ]

    print(f"\nStrategy: {strategy}")
    print(f"Feasible candidates: {len(feasible)}")

    if feasible:
        best = min(feasible, key=lambda r: r.real_losses_kw)
        print(f"Best actual losses: {best.real_losses_kw:.3f} kW")
        print(f"Closed ties: {best.plan.close_ties}")
        print(f"Opened branches: {best.plan.open_branches}")
        print(f"Minimum voltage: {best.min_voltage_pu:.6f} pu")
