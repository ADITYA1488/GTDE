from src.ieee33_network import build_ieee33_network
from src.restoration import find_restoration_plans
from src.restoration_powerflow import evaluate_ieee33_configuration

net = build_ieee33_network()

plans = find_restoration_plans(
    net,
    faulted_branches={"L15"},
    max_operations=3,
    max_results=100,
)

feasible = []

for i, plan in enumerate(plans, 1):
    result = evaluate_ieee33_configuration(
        closed_ties=set(plan.close_ties),
        opened_branches=set(plan.open_branches),
        faulted_branches={"L15"},
        capacitor_bus=33,
        capacitor_kvar=1500,
    )

    if result.get("converged") and result.get("voltage_feasible"):
        loss = result.get("real_losses_kw")
        if loss is not None:
            feasible.append((loss, plan, result))

feasible.sort(key=lambda item: item[0])

print(f"Candidates checked: {len(plans)}")
print(f"Feasible candidates: {len(feasible)}")

for loss, plan, result in feasible[:5]:
    print(
        f"loss={loss:.3f} kW, "
        f"Vmin={result['min_voltage_pu']:.4f} pu, "
        f"close={plan.close_ties}, "
        f"open={plan.open_branches}"
    )
