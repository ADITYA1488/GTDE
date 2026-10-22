from src.ieee33_network import build_ieee33_network
from src.restoration_powerflow import evaluate_restoration_plans

net = build_ieee33_network()

for fault in ["L05", "L15", "L20"]:
    for kvar in [900, 1200, 1500, 1800]:
        results = evaluate_restoration_plans(
            net,
            faulted_branches={fault},
            max_operations=3,
            max_results=10,
            capacitor_bus=33,
            capacitor_kvar=kvar,
            max_electrical_evaluations=10,
            strategy="baseline",
        )
        feasible = [
            r for r in results
            if r.converged
            and r.voltage_feasible
            and r.graph_electrical_consistent
            and r.thermal_status != "VIOLATION"
            and r.real_losses_kw is not None
        ]
        best = min(feasible, key=lambda r: r.real_losses_kw) if feasible else None
        print(
            f"fault={fault} capacitor={kvar} kvar "
            f"feasible={len(feasible)} "
            f"best_loss={best.real_losses_kw if best else None} "
            f"min_voltage={best.min_voltage_pu if best else None}"
        )
