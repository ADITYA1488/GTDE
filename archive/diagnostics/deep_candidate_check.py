from src.ieee33_network import build_ieee33_network
from src.restoration import find_restoration_plans
from src.restoration_powerflow import evaluate_ieee33_configuration

FAULTS = ["L05", "L15", "L20"]
CANDIDATE_COUNT = 100
CAPACITOR_KVAR = 1500

net = build_ieee33_network()

for fault in FAULTS:
    plans = find_restoration_plans(
        net,
        faulted_branches={fault},
        max_operations=4,
        max_results=CANDIDATE_COUNT,
    )

    feasible = []
    print(f"\nFault {fault}: checking {len(plans)} candidates")

    for i, plan in enumerate(plans, 1):
        if not plan.valid:
            continue

        result = evaluate_ieee33_configuration(
            closed_ties=set(plan.close_ties),
            opened_branches=set(plan.open_branches),
            faulted_branches={fault},
            capacitor_bus=33,
            capacitor_kvar=CAPACITOR_KVAR,
        )

        if result.get("converged") and result.get("voltage_feasible"):
            feasible.append((result.get("real_losses_kw"), plan, result))

        if i % 20 == 0:
            print(f"  Checked {i}/{len(plans)}")

    feasible.sort(key=lambda x: x[0] if x[0] is not None else float("inf"))
    print(f"Feasible candidates: {len(feasible)}")

    for loss, plan, result in feasible[:5]:
        print(
            f"  loss={loss:.3f} kW, "
            f"Vmin={result.get('min_voltage_pu'):.4f} pu, "
            f"close={plan.close_ties}, open={plan.open_branches}"
        )