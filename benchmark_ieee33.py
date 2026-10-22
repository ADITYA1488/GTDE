import csv
import time
from pathlib import Path

from src.ieee33_network import build_ieee33_network
from src.restoration_powerflow import evaluate_restoration_plans

FAULTS = ["L05", "L10", "L15", "L20", "L25", "L30"]
OUTPUT = Path("results")
OUTPUT.mkdir(exist_ok=True)

rows = []

for fault in FAULTS:
    for strategy in ("baseline", "adaptive"):
        print(f"Testing fault={fault}, strategy={strategy}...", flush=True)
        start = time.perf_counter()

        try:
            results = evaluate_restoration_plans(
                build_ieee33_network(),
                faulted_branches={fault},
                max_operations=3,
                max_results=10,
                capacitor_bus=33,
                capacitor_kvar=900,
                max_electrical_evaluations=10,
                strategy=strategy,
            )

            feasible = [
                r for r in results
                if r.converged
                and r.voltage_feasible
                and r.graph_electrical_consistent
                and r.thermal_status != "VIOLATION"
                and r.real_losses_kw is not None
            ]
            best = min(feasible, key=lambda r: r.real_losses_kw) if feasible else None

            rows.append({
                "fault": fault,
                "strategy": strategy,
                "evaluated": len(results),
                "feasible": len(feasible),
                "restored_kw": best.plan.restored_kw if best else None,
                "restoration_pct": best.plan.restoration_pct if best else None,
                "actual_losses_kw": best.real_losses_kw if best else None,
                "min_voltage_pu": best.min_voltage_pu if best else None,
                "closed_ties": ";".join(best.plan.close_ties) if best else "",
                "opened_branches": ";".join(best.plan.open_branches) if best else "",
                "thermal_status": best.thermal_status if best else "UNASSESSED",
                "runtime_seconds": round(time.perf_counter() - start, 3),
                "error": "",
            })

            if best:
                print(
                    f"  feasible={len(feasible)}, losses={best.real_losses_kw:.3f} kW, "
                    f"min_voltage={best.min_voltage_pu:.4f} pu"
                )
            else:
                print(f"  No feasible candidate among {len(results)} evaluated.")

        except Exception as exc:
            rows.append({
                "fault": fault,
                "strategy": strategy,
                "error": f"{type(exc).__name__}: {exc}",
                "runtime_seconds": round(time.perf_counter() - start, 3),
            })
            print(f"  ERROR: {type(exc).__name__}: {exc}")

with (OUTPUT / "ieee33_benchmark.csv").open("w", newline="", encoding="utf-8") as f:
    columns = [
        "fault", "strategy", "evaluated", "feasible", "restored_kw",
        "restoration_pct", "actual_losses_kw", "min_voltage_pu",
        "closed_ties", "opened_branches", "thermal_status",
        "runtime_seconds", "error",
    ]
    writer = csv.DictWriter(f, fieldnames=columns)
    writer.writeheader()
    writer.writerows(rows)

print(f"\nSaved benchmark: {OUTPUT / 'ieee33_benchmark.csv'}")
