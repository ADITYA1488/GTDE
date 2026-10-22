import csv
from pathlib import Path
from src.thermal_analysis import analyze_thermal_limits
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

VOLTAGE_MIN_PU = 0.95
VOLTAGE_MAX_PU = 1.05

EXPECTED_BUSES = 33
EXPECTED_PHASE_NODES = 99
LOAD_TOLERANCE_KW = 0.01

CAPACITOR_BUSES = [18, 25, 30, 33]
CAPACITOR_SIZES_KVAR = [150, 300, 450, 600, 900]
# Only verified ampacity ratings should be entered here.
THERMAL_AMPACITY_RATINGS_A = {}


def build_circuit(
    closed_ties=(),
    opened_branches=(),
    capacitor_bus=None,
    capacitor_kvar=0,
):
    """Build and solve one OpenDSS network configuration."""

    closed_ties = set(closed_ties)
    opened_branches = set(opened_branches)

    dss.Text.Command("Clear")
    dss.Text.Command("Set DefaultBaseFrequency=50")

    dss.Text.Command(
        f"New Circuit.IEEE33 bus1=Bus{SOURCE_BUS} "
        f"phases=3 basekV={BASE_KV} pu=1.0 frequency=50"
    )

    # Create the normally closed main branches.
    for i, (u, v, r, x) in enumerate(MAIN_BRANCHES, start=1):
        branch_id = f"L{i:02d}"
        enabled = "no" if branch_id in opened_branches else "yes"

        dss.Text.Command(
            f"New Line.{branch_id} "
            f"bus1=Bus{u}.1.2.3 bus2=Bus{v}.1.2.3 "
            f"phases=3 r1={r} x1={x} "
            f"r0={3 * r} x0={3 * x} "
            f"length=1 units=km enabled={enabled}"
        )

    # Create normally open tie branches.
    for i, (u, v, r, x) in enumerate(TIE_BRANCHES, start=33):
        branch_id = f"T{i}"
        enabled = "yes" if branch_id in closed_ties else "no"

        dss.Text.Command(
            f"New Line.{branch_id} "
            f"bus1=Bus{u}.1.2.3 bus2=Bus{v}.1.2.3 "
            f"phases=3 r1={r} x1={x} "
            f"r0={3 * r} x0={3 * x} "
            f"length=1 units=km enabled={enabled}"
        )

    # Create the loads.
    for bus, (p_kw, q_kvar) in BUS_LOADS.items():
        if bus == SOURCE_BUS or (p_kw == 0 and q_kvar == 0):
            continue

        dss.Text.Command(
            f"New Load.Load{bus} "
            f"bus1=Bus{bus}.1.2.3 phases=3 conn=wye "
            f"model=1 kV={BASE_KV} "
            f"kW={p_kw} kvar={q_kvar}"
        )

    # Optional three-phase capacitor bank.
    if capacitor_bus is not None and capacitor_kvar > 0:
        dss.Text.Command(
            f"New Capacitor.Support "
            f"bus1=Bus{capacitor_bus}.1.2.3 "
            f"phases=3 conn=wye "
            f"kV={BASE_KV} kvar={capacitor_kvar}"
        )

    # Solve the power flow.
    dss.Text.Command(f"Set VoltageBases=[{BASE_KV}]")
    dss.Text.Command("CalcVoltageBases")
    dss.Text.Command("Set Mode=Snapshot")
    dss.Text.Command("Solve")

    if not dss.Solution.Converged():
        raise RuntimeError("OpenDSS did not converge.")

    # Collect energized phase voltage magnitudes in per unit.
    voltages = []

    for bus in dss.Circuit.AllBusNames():
        dss.Circuit.SetActiveBus(bus)
        values = dss.Bus.puVmagAngle()

        voltages.extend(
            float(value)
            for value in values[0::2]
            if value > 0.01
        )

    if not voltages:
        raise RuntimeError("No energized bus voltages returned.")

    losses = dss.Circuit.Losses()
    thermal = analyze_thermal_limits(
        ampacity_ratings_a=THERMAL_AMPACITY_RATINGS_A
    )

    thermal_results = thermal["results"]

    thermal_violation_count = sum(
        result.status == "VIOLATION"
        for result in thermal_results
    )

    thermal_unassessed_count = sum(
        result.status == "UNASSESSED"
        for result in thermal_results
    )

    # Include branch-level details in the CSV for later investigation.
    thermal_branch_details = "; ".join(
        (
            f"{result.branch_id}:"
            f"{result.measured_current_a:.3f}A:"
            f"{result.status}"
        )
        for result in thermal_results
    )

    return {
        "powerflow_converged": True,
        "min_voltage_pu": min(voltages),
        "max_voltage_pu": max(voltages),
        "real_losses_kw": losses[0] / 1000,
        "reactive_losses_kvar": losses[1] / 1000,
        "energized_phase_nodes": len(voltages),
        "thermal_status": thermal["thermal_status"],
        "thermal_violation_count": thermal_violation_count,
        "thermal_unassessed_count": thermal_unassessed_count,
        "thermal_branch_count": thermal["branch_count"],
        "thermal_branch_details": thermal_branch_details,
    }


def evaluate_configuration(
    net,
    closed_ties=(),
    opened_branches=(),
    capacitor_bus=None,
    capacitor_kvar=0,
):
    """Check network topology and evaluate its electrical performance."""

    closed_ties = list(closed_ties)
    opened_branches = list(opened_branches)

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

    load_pct = (
        100 * served_load / total_load
        if total_load
        else 100.0
    )

    if not closed_ties and not opened_branches:
        configuration = "base"
    else:
        configuration = (
            f"{'_'.join(closed_ties)}_closed_"
            f"{'_'.join(opened_branches)}_open"
        )

    if capacitor_bus is None or capacitor_kvar <= 0:
        capacitor_label = "no_capacitor"
    else:
        capacitor_label = (
            f"cap_bus_{capacitor_bus}_{capacitor_kvar}_kvar"
        )

    row = {
        "configuration": configuration,
        "scenario": f"{configuration}__{capacitor_label}",
        "close_ties": ";".join(closed_ties),
        "open_branches": ";".join(opened_branches),
        "switching_operations": (
            len(closed_ties) + len(opened_branches)
        ),
        "capacitor_bus": (
            "" if capacitor_bus is None else capacitor_bus
        ),
        "capacitor_kvar": capacitor_kvar,
        "load_served_kw": round(served_load, 3),
        "load_served_pct": round(load_pct, 3),
        "supplied_bus_count": len(supplied),
        "topology_valid": not errors,
        "topology_errors": "; ".join(errors),
        "powerflow_converged": False,
        "voltage_feasible": False,

        # Existing feasibility means topology/load/voltage feasibility.
        "feasible": False,

        # Thermal compliance is separate from existing feasibility.
        "thermal_status": "UNASSESSED",
        "thermal_violation_count": 0,
        "thermal_unassessed_count": 0,
        "thermal_branch_count": 0,
        "thermal_branch_details": "",
        "thermal_feasible": None,
        "fully_assessed_feasible": False,

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
        electrical = build_circuit(
            closed_ties=closed_ties,
            opened_branches=opened_branches,
            capacitor_bus=capacitor_bus,
            capacitor_kvar=capacitor_kvar,
        )
    except RuntimeError as exc:
        row["feasibility_notes"] = str(exc)
        return row

    row.update(electrical)
    thermal_status = electrical["thermal_status"]

    if thermal_status == "VIOLATION":
        row["thermal_feasible"] = False
    elif thermal_status == "PASS":
        row["thermal_feasible"] = True
    else:
        row["thermal_feasible"] = None
        # Strict feasibility requires verified thermal compliance too.
        row["fully_assessed_feasible"] = (
                row["feasible"]
                and row["thermal_feasible"] is True
        )

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
        reasons.append(
            f"Expected {EXPECTED_PHASE_NODES} energized phase nodes; "
            f"found {electrical['energized_phase_nodes']}"
        )

    if not voltage_ok:
        reasons.append(
            f"Voltage outside [{VOLTAGE_MIN_PU}, "
            f"{VOLTAGE_MAX_PU}] pu"
        )

    row["feasible"] = (
        row["topology_valid"]
        and row["supplied_bus_count"] == EXPECTED_BUSES
        and abs(served_load - total_load) <= LOAD_TOLERANCE_KW
        and row["powerflow_converged"]
        and phase_nodes_ok
        and voltage_ok
    )

    row["feasibility_notes"] = (
        "; ".join(reasons) if reasons else "OK"
    )

    return row


def diagnostic_score(row, total_load_kw):
    """Rank candidates for diagnosis, not as a substitute for feasibility."""

    if not row.get("powerflow_converged", False):
        return float("inf")

    voltage_violation = max(
        0.0,
        VOLTAGE_MIN_PU - row["min_voltage_pu"],
    )

    voltage_violation += max(
        0.0,
        row["max_voltage_pu"] - VOLTAGE_MAX_PU,
    )

    unserved_kw = max(
        0.0,
        total_load_kw - row.get("load_served_kw", 0.0),
    )

    return (
        voltage_violation * 1000
        + unserved_kw * 100
        + row["real_losses_kw"] * 0.001
    )


def generate_switch_configurations(net):
    """Generate the base case and radial one-tie/one-line exchanges."""

    configurations = [((), ())]

    ties = [
        branch.branch_id
        for branch in net.branches
        if not branch.normally_closed and branch.switchable
    ]

    lines = [
        branch.branch_id
        for branch in net.branches
        if branch.normally_closed and branch.switchable
    ]

    base_graph = net.build_graph()
    branch_by_id = {
        branch.branch_id: branch
        for branch in net.branches
    }

    for tie in ties:
        tie_branch = branch_by_id[tie]

        path = nx.shortest_path(
            base_graph,
            source=tie_branch.u,
            target=tie_branch.v,
        )

        path_edges = {
            frozenset((u, v))
            for u, v in zip(path, path[1:])
        }

        for line in lines:
            line_branch = branch_by_id[line]

            if frozenset(
                (line_branch.u, line_branch.v)
            ) not in path_edges:
                continue

            configurations.append(((tie,), (line,)))

    return configurations


def main():
    net = build_ieee33_network()
    total_load = net.total_load_kw()
    rows = []

    switch_configurations = generate_switch_configurations(net)

    # Test each valid radial topology with no capacitor and with
    # every candidate capacitor bus/size combination.
    for closed_ties, opened_branches in switch_configurations:

        rows.append(
            evaluate_configuration(
                net,
                closed_ties=closed_ties,
                opened_branches=opened_branches,
            )
        )

        for bus in CAPACITOR_BUSES:
            for kvar in CAPACITOR_SIZES_KVAR:
                rows.append(
                    evaluate_configuration(
                        net,
                        closed_ties=closed_ties,
                        opened_branches=opened_branches,
                        capacitor_bus=bus,
                        capacitor_kvar=kvar,
                    )
                )

    # Feasible cases first; then rank by measured real losses.
    rows.sort(
        key=lambda row: (
            not row["feasible"],
            row.get("real_losses_kw", float("inf")),
        )
    )

    output = RESULTS_DIR / "combined_optimization_benchmark.csv"

    fieldnames = list(
        dict.fromkeys(
            key
            for row in rows
            for key in row
        )
    )

    with output.open(
        "w",
        newline="",
        encoding="utf-8",
    ) as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    feasible = [
        row for row in rows
        if row["feasible"]
    ]

    diagnostic_candidates = [
        row for row in rows
        if row.get("powerflow_converged", False)
        and row.get("topology_valid", False)
        and row.get("supplied_bus_count") == EXPECTED_BUSES
    ]

    print(f"Network configurations: {len(switch_configurations)}")
    print(f"Scenarios evaluated: {len(rows)}")
    print(f"Feasible scenarios: {len(feasible)}")
    print(
        f"Voltage limits: "
        f"{VOLTAGE_MIN_PU}-{VOLTAGE_MAX_PU} pu"
    )

    base = next(
        row for row in rows
        if row["configuration"] == "base"
        and row["capacitor_bus"] == ""
    )

    print(
        f"Base minimum voltage: "
        f"{base.get('min_voltage_pu', float('nan')):.6f} pu"
    )

    print(
        f"Base real losses: "
        f"{base.get('real_losses_kw', float('nan')):.3f} kW"
    )

    if feasible:
        best = min(
            feasible,
            key=lambda row: row["real_losses_kw"],
        )

        print(f"Best feasible scenario: {best['scenario']}")
        print(
            f"Minimum voltage: "
            f"{best['min_voltage_pu']:.6f} pu"
        )
        print(
            f"Maximum voltage: "
            f"{best['max_voltage_pu']:.6f} pu"
        )
        print(
            f"Real losses: "
            f"{best['real_losses_kw']:.3f} kW"
        )
        print(
            f"Load served: "
            f"{best['load_served_pct']:.3f}%"
        )

    elif diagnostic_candidates:
        best = min(
            diagnostic_candidates,
            key=lambda row: diagnostic_score(row, total_load),
        )

        print("No scenario meets all configured feasibility limits.")
        print(f"Best diagnostic candidate: {best['scenario']}")
        print(
            f"Minimum voltage: "
            f"{best['min_voltage_pu']:.6f} pu"
        )
        print(
            f"Maximum voltage: "
            f"{best['max_voltage_pu']:.6f} pu"
        )
        print(
            f"Real losses: "
            f"{best['real_losses_kw']:.3f} kW"
        )
        print(
            f"Load served: "
            f"{best['load_served_pct']:.3f}%"
        )
        print(f"Feasible: {best['feasible']}")
        print(f"Reason: {best['feasibility_notes']}")

    else:
        print(
            "No fully connected, converged candidate "
            "available for diagnosis."
        )
    thermal_assessed = [
        row for row in rows
        if row.get("thermal_status") == "PASS"
    ]

    thermal_violations = [
        row for row in rows
        if row.get("thermal_status") == "VIOLATION"
    ]

    thermal_unassessed = [
        row for row in rows
        if row.get("thermal_status") == "UNASSESSED"
    ]

    fully_assessed = [
        row for row in rows
        if row.get("fully_assessed_feasible", False)
    ]

    print("\nThermal assessment")
    print(f"Thermal PASS scenarios: {len(thermal_assessed)}")
    print(f"Thermal VIOLATION scenarios: {len(thermal_violations)}")
    print(f"Thermal UNASSESSED scenarios: {len(thermal_unassessed)}")
    print(f"Fully assessed feasible scenarios: {len(fully_assessed)}")
    print(f"Results saved: {output}")


if __name__ == "__main__":
    main()