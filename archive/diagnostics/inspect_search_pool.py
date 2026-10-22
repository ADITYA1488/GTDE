
from src.ieee33_network import build_ieee33_network
from src.restoration import find_restoration_plans

net = build_ieee33_network()

for fault in ["L05", "L15", "L20"]:
    print(f"\n{'=' * 55}")
    print(f"FAULT: {fault}")

    plans = find_restoration_plans(
        net,
        faulted_branches=[fault],
        max_operations=3,
        max_results=2000,
    )

    valid = [p for p in plans if p.valid]
    print("Valid candidates retained:", len(valid))

    for i, plan in enumerate(valid[:10], 1):
        print(
            f"{i:2}. ties={plan.close_ties}, "
            f"open={plan.open_branches}, "
            f"restored={plan.restored_kw:.1f} kW, "
            f"ops={plan.switching_operations}, "
            f"proxy={plan.estimated_loss_kw:.4f}"
        )
