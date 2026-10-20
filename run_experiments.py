import csv
from pathlib import Path

from src.demo_network import build_demo_network
from src.restoration import find_restoration_plans
from src.powerflow import evaluate_power_flow


OUTPUT_DIR = Path("results")
OUTPUT_DIR.mkdir(exist_ok=True)


def main():
    net = build_demo_network()

    scenarios = [
        {"L12"},
        {"L23"},
        {"L34"},
        {"L45"},
        {"L56"},
    ]

    rows = []

    for faulted in scenarios:
        plans = find_restoration_plans(
            net,
            faulted_branches=faulted,
            max_operations=3,
            max_results=100,
        )

        for plan in plans:
            if not plan.valid:
                continue

            result = evaluate_power_flow(
                net,
                closed_ties=set(plan.close_ties),
                opened_branches=set(plan.open_branches),
                faulted_branches=faulted,
            )

            converged = result.get("converged", False)
            vmin = result.get("minimum_bus_voltage_pu")
            vmax = result.get("maximum_bus_voltage_pu")
            losses = result.get("real_losses_kw")
            unsupplied = result.get("unsupplied_load_kw")

            voltage_ok = (
                vmin is not None
                and vmax is not None
                and vmin >= 0.95
                and vmax <= 1.05
            )

            feasible = (
                converged
                and voltage_ok
                and unsupplied is not None
                and unsupplied <= 1e-6
                and losses is not None
                and losses >= 0
            )

            rows.append({
                "fault": ",".join(sorted(faulted)),
                "close_ties": ",".join(plan.close_ties),
                "open_branches": ",".join(plan.open_branches),
                "restored_load_kw": plan.restored_kw,
                "restoration_pct": plan.restoration_pct,
                "switching_operations": plan.switching_operations,
                "converged": converged,
                "min_voltage_pu": vmin,
                "max_voltage_pu": vmax,
                "real_losses_kw": losses,
                "reactive_losses_kvar":
                    result.get("reactive_losses_kvar"),
                "unsupplied_load_kw": unsupplied,
                "voltage_ok": voltage_ok,
                "feasible": feasible,
                "error": result.get("error", ""),
            })

    output = OUTPUT_DIR / "restoration_experiments.csv"

    columns = [
        "fault", "close_ties", "open_branches",
        "restored_load_kw", "restoration_pct",
        "switching_operations", "converged",
        "min_voltage_pu", "max_voltage_pu",
        "real_losses_kw", "reactive_losses_kvar",
        "unsupplied_load_kw", "voltage_ok",
        "feasible", "error",
    ]

    with output.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)

    feasible_rows = [row for row in rows if row["feasible"]]

    print(f"Candidates evaluated: {len(rows)}")
    print(f"Electrically feasible candidates: {len(feasible_rows)}")
    print(f"Results saved to: {output}")

    feasible_rows.sort(key=lambda row: row["real_losses_kw"])

    for row in feasible_rows[:10]:
        print(
            f"Fault={row['fault']} | "
            f"Close={row['close_ties'] or '-'} | "
            f"Open={row['open_branches'] or '-'} | "
            f"Load={row['restored_load_kw']:.1f} kW | "
            f"Loss={row['real_losses_kw']:.4f} kW | "
            f"Operations={row['switching_operations']}"
        )


if __name__ == "__main__":
    main()