
import csv
from pathlib import Path

from opendssdirect import dss

from src.ieee33_electrical_data import (
    MAIN_BRANCHES,
    TIE_BRANCHES,
    BUS_LOADS,
    BASE_KV,
    SOURCE_BUS,
)

ROOT = Path(__file__).resolve().parent
RESULTS_DIR = ROOT / "results"
RESULTS_DIR.mkdir(exist_ok=True)

VOLTAGE_MIN_PU = 0.95
VOLTAGE_MAX_PU = 1.05

# Trial three-phase capacitor-bank ratings, in total kVAr per bank.
CAPACITOR_SIZES_KVAR = [150, 300, 450, 600, 900]

# Candidate locations; compare them rather than assuming one is optimal.
CAPACITOR_BUSES = [18, 25, 30, 33]


def solve_case(capacitor_bus=None, capacitor_kvar=0,
               closed_ties=(), opened_branches=()):
    """Build and solve one IEEE 33-bus case with optional capacitor support."""
    closed_ties = set(closed_ties)
    opened_branches = set(opened_branches)

    dss.Text.Command("Clear")
    dss.Text.Command("Set DefaultBaseFrequency=50")
    dss.Text.Command(
        f"New Circuit.IEEE33 bus1=Bus{SOURCE_BUS} "
        f"phases=3 basekV={BASE_KV} pu=1.0 frequency=50"
    )

    for i, (u, v, r, x) in enumerate(MAIN_BRANCHES, start=1):
        branch_id = f"L{i:02d}"
        enabled = "no" if branch_id in opened_branches else "yes"
        dss.Text.Command(
            f"New Line.{branch_id} bus1=Bus{u}.1.2.3 "
            f"bus2=Bus{v}.1.2.3 phases=3 "
            f"r1={r} x1={x} r0={3*r} x0={3*x} "
            f"length=1 units=km enabled={enabled}"
        )

    for i, (u, v, r, x) in enumerate(TIE_BRANCHES, start=33):
        branch_id = f"T{i}"
        enabled = "yes" if branch_id in closed_ties else "no"
        dss.Text.Command(
            f"New Line.{branch_id} bus1=Bus{u}.1.2.3 "
            f"bus2=Bus{v}.1.2.3 phases=3 "
            f"r1={r} x1={x} r0={3*r} x0={3*x} "
            f"length=1 units=km enabled={enabled}"
        )

    for bus, (p_kw, q_kvar) in BUS_LOADS.items():
        if bus == SOURCE_BUS or (p_kw == 0 and q_kvar == 0):
            continue
        dss.Text.Command(
            f"New Load.Load{bus} bus1=Bus{bus}.1.2.3 "
            f"phases=3 conn=wye model=1 kV={BASE_KV} "
            f"kW={p_kw} kvar={q_kvar}"
        )

    if capacitor_bus is not None and capacitor_kvar > 0:
        dss.Text.Command(
            f"New Capacitor.Support bus1=Bus{capacitor_bus}.1.2.3 "
            f"phases=3 conn=wye kV={BASE_KV} kvar={capacitor_kvar}"
        )

    dss.Text.Command(f"Set VoltageBases=[{BASE_KV}]")
    dss.Text.Command("CalcVoltageBases")
    dss.Text.Command("Set Mode=Snapshot")
    dss.Text.Command("Solve")

    if not dss.Solution.Converged():
        raise RuntimeError("OpenDSS did not converge.")

    voltages = []
    for bus in dss.Circuit.AllBusNames():
        dss.Circuit.SetActiveBus(bus)
        values = dss.Bus.puVmagAngle()
        voltages.extend(float(v) for v in values[0::2] if v > 0.01)

    if len(voltages) != 99:
        raise RuntimeError(
            f"Expected 99 energized phase nodes; found {len(voltages)}."
        )

    losses = dss.Circuit.Losses()
    min_v = min(voltages)
    max_v = max(voltages)

    return {
        "converged": True,
        "min_voltage_pu": min_v,
        "max_voltage_pu": max_v,
        "real_losses_kw": losses[0] / 1000,
        "reactive_losses_kvar": losses[1] / 1000,
        "voltage_feasible": (
            VOLTAGE_MIN_PU <= min_v and max_v <= VOLTAGE_MAX_PU
        ),
    }


def main():
    rows = []

    # Reference case with no capacitor support.
    base = solve_case()
    rows.append({
        "scenario": "base",
        "capacitor_bus": "",
        "capacitor_kvar": 0,
        **base,
    })

    # Sweep candidate locations and trial capacitor sizes.
    for bus in CAPACITOR_BUSES:
        for kvar in CAPACITOR_SIZES_KVAR:
            try:
                result = solve_case(capacitor_bus=bus, capacitor_kvar=kvar)
                rows.append({
                    "scenario": f"capacitor_bus_{bus}_{kvar}_kvar",
                    "capacitor_bus": bus,
                    "capacitor_kvar": kvar,
                    **result,
                })
            except RuntimeError as exc:
                rows.append({
                    "scenario": f"capacitor_bus_{bus}_{kvar}_kvar",
                    "capacitor_bus": bus,
                    "capacitor_kvar": kvar,
                    "converged": False,
                    "voltage_feasible": False,
                    "error": str(exc),
                })

    feasible = [
        row for row in rows
        if row.get("converged") and row.get("voltage_feasible")
    ]

    output = RESULTS_DIR / "voltage_support_benchmark.csv"
    fields = list(dict.fromkeys(key for row in rows for key in row))
    with output.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)

    print(f"Scenarios evaluated: {len(rows)}")
    print(f"Voltage-feasible scenarios: {len(feasible)}")
    print(f"Base minimum voltage: {base['min_voltage_pu']:.6f} pu")
    print(f"Base real losses: {base['real_losses_kw']:.3f} kW")

    if feasible:
        best = min(feasible, key=lambda row: row["real_losses_kw"])
        print(f"Best feasible scenario: {best['scenario']}")
        print(f"Minimum voltage: {best['min_voltage_pu']:.6f} pu")
        print(f"Real losses: {best['real_losses_kw']:.3f} kW")
    else:
        print("No tested scenario meets the voltage limits.")

    print(f"Results saved: {output}")


if __name__ == "__main__":
    main()
