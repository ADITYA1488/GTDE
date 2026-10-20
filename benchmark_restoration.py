import networkx as nx
import time
from src.ieee33_network import build_ieee33_network
from src.restoration import find_restoration_plans

net = build_ieee33_network()
faults = ["L05", "L10", "L15", "L20", "L25", "L30"]

print("IEEE 33-BUS RESTORATION BENCHMARK")
print("-" * 55)

for fault in faults:
    start = time.perf_counter()

    plans = find_restoration_plans(
        net,
        faulted_branches=[fault],
        max_operations=1,
        max_results=10,
    )
    for plan in plans:
        graph = net.build_graph(
            plan.close_ties,
            plan.open_branches,
            [fault],
        )
        radial = nx.is_forest(graph)

        print(
            f"{fault} | valid={plan.valid} | radial={radial} "
            f"| restored={plan.restoration_pct:.2f}% "
            f"| close={plan.close_ties} "
            f"| open={plan.open_branches}"
        )

        assert plan.valid and radial, f"Invalid plan for {fault}: {plan}"
        assert nx.is_forest(graph), (
            f"Non-radial plan found for {fault}: {plan}"
        )

    elapsed = time.perf_counter() - start
    valid = [p for p in plans if p.valid]
    best = valid[0] if valid else None

    if best:
        print(
            f"{fault}: restored={best.restoration_pct:.2f}% | "
            f"operations={best.switching_operations} | "
            f"close={best.close_ties} | "
            f"open={best.open_branches} | "
            f"time={elapsed:.3f}s"
        )
    else:
        print(f"{fault}: no valid plan | time={elapsed:.3f}s")
