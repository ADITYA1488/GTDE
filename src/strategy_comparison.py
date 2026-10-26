
from time import perf_counter

from src.restoration_reporting import classify_candidates
from src.restoration_powerflow import evaluate_restoration_plans


def compare_strategies(
    net,
    faulted_branches,
    max_operations=3,
    evaluation_budget=10,
    capacitor_bus=33,
    capacitor_kvar=900,
):
    """Compare baseline and adaptive using identical scenario settings."""

    comparison = []

    for strategy in ("baseline", "adaptive"):
        start = perf_counter()

        results = evaluate_restoration_plans(
            net,
            faulted_branches=set(faulted_branches),
            max_operations=max_operations,
            max_results=10,
            capacitor_bus=capacitor_bus,
            capacitor_kvar=capacitor_kvar,
            max_electrical_evaluations=evaluation_budget,
            strategy=strategy,
        )

        elapsed = perf_counter() - start

        groups = classify_candidates(results)
        electrically_feasible = groups["electrically_feasible"]
        fully_verified = groups["fully_verified"]

        best = max(
            electrically_feasible,
            key=lambda result: (
                result.plan.restored_kw,
                -(result.real_losses_kw or float("inf")),
            ),
            default=None,
        )

        comparison.append({
            "Strategy": strategy,
            "Candidates returned": len(results),
            "Electrically feasible candidates": len(electrically_feasible),
            "Fully verified candidates": len(fully_verified),
            "Best graph-connected load (kW)": (
                best.plan.restored_kw if best else None
            ),
            "Graph-connected restoration (%)": (
                best.plan.restoration_pct if best else None
            ),
            "Minimum voltage (pu)": (
                best.min_voltage_pu if best else None
            ),
            "Real losses (kW)": (
                best.real_losses_kw if best else None
            ),
            "Switching operations": (
                best.plan.switching_operations if best else None
            ),
            "Runtime (s)": round(elapsed, 3),
            "Thermal status": best.thermal_status if best else "UNASSESSED",
        })

    return comparison
