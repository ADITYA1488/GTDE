from src.ieee33_network import build_ieee33_network
from src.restoration_powerflow import evaluate_restoration_plans

net = build_ieee33_network()

for fault in ["L05", "L15", "L20"]:
    results = evaluate_restoration_plans(
        net,
        faulted_branches={fault},
        max_operations=3,
        max_results=10,
        capacitor_bus=33,
        capacitor_kvar=900,
        max_electrical_evaluations=10,
        strategy="baseline",
    )

    print(f"\nFAULT: {fault}")
    for r in results:
        print(
            "ties=", r.plan.close_ties,
            "open=", r.plan.open_branches,
            "valid=", r.plan.valid,
            "converged=", r.converged,
            "voltage_feasible=", r.voltage_feasible,
            "min_voltage=", r.min_voltage_pu,
            "reason=", r.rejection_reason,
        )
