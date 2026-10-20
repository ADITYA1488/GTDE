
import time
from src.ieee33_network import build_ieee33_network
from src.restoration import find_restoration_plans

net = build_ieee33_network()

for max_ops in (1, 2, 3):
    start = time.perf_counter()

    plans = find_restoration_plans(
        net,
        faulted_branches=["L05"],
        max_operations=max_ops,
        max_results=10,
    )

    elapsed = time.perf_counter() - start
    valid_plans = [p for p in plans if p.valid]

    print(
        f"max_ops={max_ops} | returned={len(plans)} "
        f"| valid={len(valid_plans)} | elapsed={elapsed:.3f}s"
    )
