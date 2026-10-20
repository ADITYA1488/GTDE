
import csv
from pathlib import Path

import networkx as nx
from opendssdirect import dss

from src.ieee33_electrical_data import (
    MAIN_BRANCHES,
    TIE_BRANCHES,
    BUS_LOADS,
    BASE_KV,
    SOURCE_BUS,
)
from src.ieee33_network import build_ieee33_network

ROOT = Path(__file__).resolve().parent
RESULTS_DIR = ROOT / "results"
RESULTS_DIR.mkdir(exist_ok=True)

# Configurable operating limits (per unit).
VOLTAGE_MIN_PU = 0.95
VOLTAGE_MAX_PU = 1.05
EXPECTED_BUSES = 33
EXPECTED_PHASE_NODES = EXPECTED_BUSES * 3
LOAD_TOLERANCE_KW = 0.01


def build_circuit(closed_ties=(), opened_branches=()):
    """Solve a switch configuration and return actual OpenDSS measurements."""
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
            f"New Line.{branch_id} "
            f"bus1=Bus{u}.1.2.3 bus2=Bus{v}.1.2.3 "
            f"phases=3 r1={r} x1={x} r0={3*r} x0={3*x} "
            f"length=1 units=km enabled={enabled}"
        )

    for i, (u, v, r, x) in enumerate(TIE_BRANCHES, start=33):
        branch_id = f"T{i}"
        enabled = "yes" if branch_id in closed_ties else "no"

        dss.Text.Command(
            f"New Line.{branch_id} "
            f"bus1=Bus{u}.1.2.3 bus2=Bus{v}.1.2.3 "
            f"phases=3 r1={r} x1={x} r0={3*r} x0={3*x} "
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
        voltages.extend(
            float(value) for value in values[0::2]
            if value > 0.01
        )

    if not voltages:
        raise RuntimeError("No energized bus voltages returned.")

    losses = dss.Circuit.Losses()
    return {
        "min_voltage_pu": min(voltages),
        "max_voltage_pu": max(voltages),
        "real_losses_kw": losses[0] / 1000,
        "reactive_losses_kvar": losses[1] / 1000,
        "energized_phase_nodes": len(voltages),
    }


def evaluate_configuration(net, closed_ties=(), opened_branches=()):
    """Check topology, load service, convergence and voltage constraints."""
    errors = net.validate_topology(
        closed_ties=closed_ties,
        opened_branches=opened_branches,
    )
    graph = net.build_graph(
        closed_ties=closed_ties,
        opened_branches=opened_branches,
    )

    supplied = net.supplied_buses(graph)
    total_load = net.total_load_kw()
    served_load = net.restored_load_kw(graph)
    load_pct = 100 * served_load / total_load if total_load else 100.0

    row = {
        "configuration": (
            "base" if not closed_ties and not opened_branches
            else f"{'_'.join(closed_ties)}_closed_"
                 f"{'_'.join(opened_branches)}_open"
        ),
        "close_ties": ";".join(closed_ties),
        "open_branches": ";".join(opened_branches),
        "switching_operations": len(closed_ties) + len(opened_branches),
        "load_served_kw": round(served_load, 3),
        "load_served_pct": round(load_pct, 3),
        "supplied_bus_count": len(supplied),
        "topology_valid": not errors,
        "topology_errors": "; ".join(errors),
        "powerflow_converged": False,
        "voltage_feasible": False,
        "feasible": False,
        "feasibility_notes": "",
    }

    if errors:
        row["feasibility_notes"] = "Topology validation failed"
        return row

    if len(supplied) != EXPECTED_BUSES:
        row["feasibility_notes"] = "Not all buses are supplied"
        return row

    if abs(served_load - total_load) > LOAD_TOLERANCE_KW:
        row["feasibility_notes"] = "Not all load is served"
        return row

    try:
        electrical = build_circuit(closed_ties, opened_branches)
    except RuntimeError as exc:
        row["feasibility_notes"] = str(exc)
        return row

    row.update(electrical)
    row["powerflow_converged"] = True

    phase_nodes_ok = (
        electrical["energized_phase_nodes"] == EXPECTED_PHASE_NODES
    )
    voltage_ok = (
        VOLTAGE_MIN_PU <= electrical["min_voltage_pu"]
        and electrical["max_voltage_pu"] <= VOLTAGE_MAX_PU
    )
    row["voltage_feasible"] = voltage_ok

    reasons = []
    if not phase_nodes_ok:
        reasons.append("Expected 99 energized phase nodes")
    if not voltage_ok:
        reasons.append(
            f"Voltage outside [{VOLTAGE_MIN_PU}, {VOLTAGE_MAX_PU}] pu"
        )

    row["feasible"] = (
        row["topology_valid"]
        and row["supplied_bus_count"] == EXPECTED_BUSES
        and abs(served_load - total_load) <= LOAD_TOLERANCE_KW
        and row["powerflow_converged"]
        and phase_nodes_ok
        and voltage_ok
    )
    row["feasibility_notes"] = "; ".join(reasons) if reasons else "OK"
    return row


def diagnostic_score(row):
    """Rank candidates for diagnosis; this is not an operating-feasibility test."""
    if not row.get("powerflow_converged", False):
        return float("inf")

    voltage = row["min_voltage_pu"]
    voltage_violation = max(0.0, VOLTAGE_MIN_PU - voltage)
    voltage_violation += max(
        0.0, row["max_voltage_pu"] - VOLTAGE_MAX_PU
    )

    # Prioritize full load service and voltage compliance, then losses.
    unserved_kw = max(0.0, row.get("load_served_kw", 0.0))
    total_load = build_ieee33_network().total_load_kw()
    unserved_kw = max(0.0, total_load - row.get("load_served_kw", 0.0))

    return (
        voltage_violation * 1000
        + unserved_kw * 100
        + row["real_losses_kw"] * 0.001
    )


def main():
    net = build_ieee33_network()
    rows = []

    # Evaluate the base case and every one-tie/one-line exchange.
    rows.append(evaluate_configuration(net))

    ties = [
        b.branch_id for b in net.branches
        if not b.normally_closed and b.switchable
    ]
    lines = [
        b.branch_id for b in net.branches
        if b.normally_closed and b.switchable
    ]


    # Generate only switch exchanges that preserve a connected radial network.
    # Closing a tie creates one cycle; opening a main branch on the
    # existing path between the tie endpoints breaks that cycle.
    base_graph = net.build_graph()
    branch_by_id = {b.branch_id: b for b in net.branches}

    for tie in ties:
        tie_branch = branch_by_id[tie]
        path = nx.shortest_path(
            base_graph, source=tie_branch.u, target=tie_branch.v
        )
        path_edges = {
            frozenset((u, v))
            for u, v in zip(path, path[1:])
        }

        for line in lines:
            line_branch = branch_by_id[line]
            if frozenset((line_branch.u, line_branch.v)) not in path_edges:
                continue

            rows.append(
                evaluate_configuration(
                    net,
                    closed_ties=[tie],
                    opened_branches=[line],
                )
            )


    # Keep every evaluated configuration in the CSV for transparency.
    rows.sort(key=lambda row: (
        not row["feasible"],
        row.get("real_losses_kw", float("inf")),
    ))

    output = RESULTS_DIR / "reconfiguration_benchmark.csv"
    fieldnames = list(dict.fromkeys(
        key for row in rows for key in row
    ))
    with output.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


    feasible = [row for row in rows if row["feasible"]]
    diagnostic_candidates = [
        row for row in rows
        if row.get("powerflow_converged", False)
        and row.get("topology_valid", False)
        and row.get("supplied_bus_count") == EXPECTED_BUSES
    ]

    print(f"Configurations evaluated: {len(rows)}")
    print(f"Feasible configurations: {len(feasible)}")
    print(f"Voltage limits: {VOLTAGE_MIN_PU}-{VOLTAGE_MAX_PU} pu")

    base = next(row for row in rows if row["configuration"] == "base")
    print(f"Base-case losses: {base.get('real_losses_kw', float('nan')):.3f} kW")

    if feasible:
        best = min(feasible, key=lambda row: row["real_losses_kw"])
        print(f"Best feasible configuration: {best['configuration']}")
        print(f"Real losses: {best['real_losses_kw']:.3f} kW")
        print(f"Minimum voltage: {best['min_voltage_pu']:.6f} pu")
        print(f"Load served: {best['load_served_pct']:.3f}%")
    elif diagnostic_candidates:
        best = min(diagnostic_candidates, key=diagnostic_score)
        print("No configuration meets all configured feasibility limits.")
        print(f"Best diagnostic candidate: {best['configuration']}")
        print(f"Real losses: {best['real_losses_kw']:.3f} kW")
        print(f"Minimum voltage: {best['min_voltage_pu']:.6f} pu")
        print(f"Load served: {best['load_served_pct']:.3f}%")
        print(f"Feasible: {best['feasible']}")
        print(f"Reason: {best['feasibility_notes']}")
    else:
        print("No fully connected, converged candidate available for diagnosis.")

    print(f"Results saved: {output}")



if __name__ == "__main__":

    main()
