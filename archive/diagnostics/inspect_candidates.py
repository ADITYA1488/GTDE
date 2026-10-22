from src.ieee33_network import build_ieee33_network
from src.restoration import find_restoration_plans

net = build_ieee33_network()

for fault in ["L05", "L20"]:
    plans = find_restoration_plans(
        net,
        faulted_branches={fault},
        max_operations=4,
        max_results=2000,
    )

    valid = [p for p in plans if p.valid]
    print(
        f"{fault}: returned={len(plans)}, "
        f"graph_valid={len(valid)}"
    )

    for p in valid[:5]:
        print(
            "  close=", p.close_ties,
            "open=", p.open_branches,
            "restored=", p.restored_kw,
            "operations=", p.switching_operations,
        )
