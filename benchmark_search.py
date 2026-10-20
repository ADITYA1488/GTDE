
from time import perf_counter

from src.ieee33_network import build_ieee33_network
from src.restoration import find_restoration_plans
from src.restoration_powerflow import evaluate_restoration_plans


def main():
    net = build_ieee33_network()
    faulted_branches = {"L10"}

    print("=" * 60)
    print("GTDE SEARCH PERFORMANCE BENCHMARK")
    print("=" * 60)
    print(f"Faulted branches: {sorted(faulted_branches)}")
    print("Maximum switching operations: 3")
    print("Electrical evaluation budget: 10")
    print()

    # Benchmark 1: Graph candidate generation and ranking.
    start = perf_counter()

    plans = find_restoration_plans(
        net,
        faulted_branches=faulted_branches,
        max_operations=3,
        max_results=10**9,
    )

    graph_time = perf_counter() - start
    valid_plans = [plan for plan in plans if plan.valid]

    print("GRAPH SEARCH")
    print("-" * 60)
    print(f"Total plans returned: {len(plans)}")
    print(f"Valid plans:          {len(valid_plans)}")
    print(f"Elapsed time:         {graph_time:.4f} seconds")
    print()

    # Benchmark 2: Bounded search with electrical evaluation.
    start = perf_counter()

    results = evaluate_restoration_plans(
        net,
        faulted_branches=faulted_branches,
        max_operations=3,
        max_results=10,
        capacitor_bus=33,
        capacitor_kvar=900,
        max_electrical_evaluations=10,
    )

    total_time = perf_counter() - start

    print("BOUNDED ELECTRICAL SEARCH")
    print("-" * 60)
    print(f"Results returned:     {len(results)}")
    print(f"Evaluation budget:    10")
    print(f"Elapsed time:         {total_time:.4f} seconds")
    print()

    print("TOP RESULTS")
    print("-" * 60)

    for index, result in enumerate(results, start=1):
        print(
            f"{index}. "
            f"Close={result.plan.close_ties}, "
            f"Open={result.plan.open_branches}, "
            f"Restored={result.plan.restored_kw:.1f} kW, "
            f"Converged={result.converged}, "
            f"Voltage feasible={result.voltage_feasible}, "
            f"Losses={result.real_losses_kw}"
        )

    print()
    print("NOTE")
    print("-" * 60)
    print(
        "The second timing includes graph search and OpenDSS evaluations. "
        "It is not the time for electrical simulation alone."
    )
    print(
        "The graph loss proxy is not a physical power-loss calculation. "
        "Thermal compliance remains UNASSESSED without verified ratings."
    )


if __name__ == "__main__":
    main()
