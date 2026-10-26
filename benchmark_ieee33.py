import csv
import os
import time
from pathlib import Path

from src.ieee33_network import build_ieee33_network
from src.restoration_reporting import classify_candidates
from src.restoration_powerflow import evaluate_restoration_plans

FAULTS = ["L05", "L10", "L15", "L20", "L25", "L30"]
CAPACITOR_BUS = 33
CAPACITOR_KVAR = 900
OUTPUT = Path(os.environ.get("GRIDRESQ_RESULTS_DIR", "results"))
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
                capacitor_bus=CAPACITOR_BUS,
                capacitor_kvar=CAPACITOR_KVAR,
                max_electrical_evaluations=10,
                strategy=strategy,
            )

            groups = classify_candidates(results)
            electrically_feasible = groups["electrically_feasible"]
            fully_verified = groups["fully_verified"]
            # Preserve the historical best-result filter and `feasible`
            # field while exposing its electrical/thermal scope separately.
            loss_summary_candidates = [
                r for r in electrically_feasible
                if r.thermal_status != "VIOLATION"
                and r.real_losses_kw is not None
            ]
            best = (
                min(loss_summary_candidates, key=lambda r: r.real_losses_kw)
                if loss_summary_candidates else None
            )

            rows.append({
                "fault": fault,
                "strategy": strategy,
                "capacitor_bus": CAPACITOR_BUS,
                "capacitor_kvar": CAPACITOR_KVAR,
                "evaluated": len(results),
                "feasible": len(loss_summary_candidates),
                "feasibility_scope": "electrical checks; thermal may be UNASSESSED",
                "electrically_feasible_candidates": len(electrically_feasible),
                "fully_verified_candidates": len(fully_verified),
                "verification_scope": (
                    "convergence, voltage, graph consistency, thermal PASS"
                ),
                "restored_kw": best.plan.restored_kw if best else None,
                "restoration_pct": best.plan.restoration_pct if best else None,
                "graph_connected_load_kw": best.plan.restored_kw if best else None,
                "graph_connected_restoration_pct": best.plan.restoration_pct if best else None,
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
                    f"  electrically_feasible={len(electrically_feasible)}, "
                    f"fully_verified={len(fully_verified)}, "
                    f"losses={best.real_losses_kw:.3f} kW, "
                    f"min_voltage={best.min_voltage_pu:.4f} pu"
                )
            else:
                if electrically_feasible:
                    print(
                        f"  electrically_feasible={len(electrically_feasible)}, "
                        "but no candidate is eligible for the loss summary; "
                        f"fully_verified={len(fully_verified)}."
                    )
                else:
                    print(
                        f"  No electrically feasible candidate among "
                        f"{len(results)} evaluated; "
                        f"fully_verified={len(fully_verified)}."
                    )

        except Exception as exc:
            rows.append({
                "fault": fault,
                "strategy": strategy,
                "capacitor_bus": CAPACITOR_BUS,
                "capacitor_kvar": CAPACITOR_KVAR,
                "error": f"{type(exc).__name__}: {exc}",
                "runtime_seconds": round(time.perf_counter() - start, 3),
            })
            print(f"  ERROR: {type(exc).__name__}: {exc}")

with (OUTPUT / "ieee33_benchmark.csv").open("w", newline="", encoding="utf-8") as f:
    columns = [
        "fault", "strategy", "evaluated", "feasible", "restored_kw",
        "restoration_pct", "actual_losses_kw", "min_voltage_pu",
        "closed_ties", "opened_branches", "thermal_status",
        "runtime_seconds", "error", "electrically_feasible_candidates",
        "feasibility_scope",
        "fully_verified_candidates", "graph_connected_load_kw",
        "graph_connected_restoration_pct", "verification_scope",
        "capacitor_bus", "capacitor_kvar",
    ]
    writer = csv.DictWriter(f, fieldnames=columns)
    writer.writeheader()
    writer.writerows(rows)

print(f"\nSaved benchmark: {OUTPUT / 'ieee33_benchmark.csv'}")
