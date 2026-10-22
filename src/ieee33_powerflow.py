
from opendssdirect import dss

from src.thermal_analysis import analyze_thermal_limits
from src.ieee33_electrical_data import (
    BASE_KV,
    SOURCE_BUS,
    MAIN_BRANCHES,
    TIE_BRANCHES,
    BUS_LOADS,
)


def build_ieee33_circuit(
    closed_ties=(),
    opened_branches=(),
    faulted_branches=(),
    capacitor_bus=None,
    capacitor_kvar=0,
):
    """Build the IEEE 33-bus circuit for a specified switching state.

    Faulted branches are disabled and cannot be re-energized.
    Capacitor support is optional.
    """
    closed_ties = set(closed_ties)
    opened_branches = set(opened_branches)
    faulted_branches = set(faulted_branches)

    known_main = {
        f"L{i:02d}" for i in range(1, len(MAIN_BRANCHES) + 1)
    }
    known_ties = {
        f"T{i}" for i in range(33, 33 + len(TIE_BRANCHES))
    }
    known_branches = known_main | known_ties

    requested = closed_ties | opened_branches | faulted_branches
    unknown = requested - known_branches

    if unknown:
        raise ValueError(
            f"Unknown branch IDs: {', '.join(sorted(unknown))}"
        )

    conflicts = faulted_branches & (closed_ties | opened_branches)
    if conflicts:
        raise ValueError(
            "Faulted branches cannot also be switched: "
            + ", ".join(sorted(conflicts))
        )

    invalid_ties = closed_ties & known_main
    invalid_main = opened_branches & known_ties

    if invalid_ties:
        raise ValueError(
            "Only normally-open tie branches may be closed: "
            + ", ".join(sorted(invalid_ties))
        )

    if invalid_main:
        raise ValueError(
            "Only normally-closed main branches may be opened: "
            + ", ".join(sorted(invalid_main))
        )

    if capacitor_bus is not None and capacitor_bus not in BUS_LOADS:
        raise ValueError(f"Unknown capacitor bus: {capacitor_bus}")

    if capacitor_kvar < 0:
        raise ValueError("capacitor_kvar must be non-negative")

    # Reset the previous circuit before creating any elements.
    dss.Basic.ClearAll()
    dss.Text.Command("Set DefaultBaseFrequency=50")

    dss.Text.Command(
        f"New Circuit.IEEE33 "
        f"bus1=Bus{SOURCE_BUS} "
        f"phases=3 basekV={BASE_KV} pu=1.0 "
        f"frequency=50"
    )

    # Normally-closed main branches.
    for i, (u, v, r, x) in enumerate(MAIN_BRANCHES, start=1):
        branch_id = f"L{i:02d}"

        enabled = (
            "no"
            if branch_id in opened_branches
            or branch_id in faulted_branches
            else "yes"
        )

        dss.Text.Command(
            f"New Line.{branch_id} "
            f"bus1=Bus{u}.1.2.3 bus2=Bus{v}.1.2.3 "
            f"phases=3 r1={r} x1={x} "
            f"r0={3 * r} x0={3 * x} "
            f"length=1 units=km enabled={enabled}"
        )

    # Normally-open ties are enabled only when explicitly closed.
    for i, (u, v, r, x) in enumerate(TIE_BRANCHES, start=33):
        branch_id = f"T{i}"

        enabled = (
            "yes"
            if branch_id in closed_ties
            and branch_id not in faulted_branches
            else "no"
        )

        dss.Text.Command(
            f"New Line.{branch_id} "
            f"bus1=Bus{u}.1.2.3 bus2=Bus{v}.1.2.3 "
            f"phases=3 r1={r} x1={x} "
            f"r0={3 * r} x0={3 * x} "
            f"length=1 units=km enabled={enabled}"
        )

    # Create the original loads.
    for bus, (p_kw, q_kvar) in BUS_LOADS.items():
        if bus == SOURCE_BUS or (p_kw == 0 and q_kvar == 0):
            continue

        dss.Text.Command(
            f"New Load.Load{bus} "
            f"bus1=Bus{bus}.1.2.3 phases=3 conn=wye "
            f"model=1 kV={BASE_KV} "
            f"kW={p_kw} kvar={q_kvar}"
        )

    # Create the optional capacitor exactly once, outside the load loop.
    if capacitor_bus is not None and capacitor_kvar > 0:
        dss.Text.Command(
            "New Capacitor.Support "
            f"bus1=Bus{capacitor_bus}.1.2.3 "
            f"phases=3 conn=wye "
            f"kV={BASE_KV} kvar={capacitor_kvar}"
        )

    dss.Text.Command(f"Set VoltageBases=[{BASE_KV}]")
    dss.Text.Command("CalcVoltageBases")



def evaluate_ieee33_configuration(
    closed_ties=(),
    opened_branches=(),
    faulted_branches=(),
    capacitor_bus=None,
    capacitor_kvar=0,
    ampacity_ratings_a=None,
):
    """Solve one configuration and return electrical metrics.

    Thermal compliance remains UNASSESSED until verified ampacity
    ratings are available.
    """
    build_ieee33_circuit(
        closed_ties=closed_ties,
        opened_branches=opened_branches,
        faulted_branches=faulted_branches,
        capacitor_bus=capacitor_bus,
        capacitor_kvar=capacitor_kvar,
    )

    dss.Text.Command("Set Mode=Snapshot")
    dss.Text.Command("Solve")

    converged = bool(dss.Solution.Converged())

    if not converged:
        # Capture the solver state rather than silently hiding it.
        try:
            iterations = dss.Solution.Iterations()
        except Exception:
            iterations = None

        return {
            "converged": False,
            "voltage_feasible": False,
            "min_voltage_pu": None,
            "max_voltage_pu": None,
            "energized_phase_nodes": 0,
            "energized_buses": [],
            "real_losses_kw": None,
            "thermal_status": "UNASSESSED",
            "solver_diagnostic": (
                f"OpenDSS did not converge; iterations={iterations}"
            ),
        }

    voltages = []
    energized_buses = []

    for bus in dss.Circuit.AllBusNames():
        dss.Circuit.SetActiveBus(bus)
        values = dss.Bus.puVmagAngle()

        # Magnitude/angle pairs: use positive, finite voltage magnitudes.
        bus_voltages = [
            float(value)
            for value in values[0::2]
            if value is not None and 0.01 < float(value) < float("inf")
        ]

        if not bus_voltages:
            continue

        voltages.extend(bus_voltages)

        normalized_name = bus.split(".")[0].lower()
        if normalized_name.startswith("bus"):
            suffix = normalized_name[3:]
            if suffix.isdigit():
                energized_buses.append(int(suffix))

    energized_buses = sorted(set(energized_buses))

    if not voltages:
        return {
            "converged": True,
            "voltage_feasible": False,
            "min_voltage_pu": None,
            "max_voltage_pu": None,
            "energized_phase_nodes": 0,
            "energized_buses": [],
            "real_losses_kw": None,
            "thermal_status": "UNASSESSED",
            "solver_diagnostic": (
                "OpenDSS reported convergence but returned no usable voltages."
            ),
        }

    losses = dss.Circuit.Losses()
    min_v = min(voltages)
    max_v = max(voltages)

    # Missing ampacity data must never be interpreted as thermally safe.
    if ampacity_ratings_a:
        thermal = analyze_thermal_limits(ampacity_ratings_a)
        thermal_status = thermal["thermal_status"]
        thermal_results = [
            {
                "branch_id": item.branch_id,
                "measured_current_a": item.measured_current_a,
                "ampacity_a": item.ampacity_a,
                "status": item.status,
                "margin_a": item.margin_a,
                "loading_pct": item.loading_pct,
                "message": item.message,
            }
            for item in thermal["results"]
        ]
    else:
        thermal_status = "UNASSESSED"
        thermal_results = []



    return {
        "converged": True,
        "voltage_feasible": min_v >= 0.95 and max_v <= 1.05,
        "min_voltage_pu": min_v,
        "max_voltage_pu": max_v,
        "energized_phase_nodes": len(voltages),
        "energized_buses": energized_buses,
        "real_losses_kw": losses[0] / 1000,
        "thermal_status": thermal_status,
        "thermal_results": thermal_results,
        "solver_diagnostic": None,
    }


def solve_ieee33():
    """Solve and print baseline IEEE 33-bus feeder results."""
    build_ieee33_circuit()

    dss.Text.Command("Set Mode=Snapshot")
    dss.Text.Command("Solve")

    if not dss.Solution.Converged():
        raise RuntimeError("OpenDSS power flow failed to converge.")

    bus_names = list(dss.Circuit.AllBusNames())
    voltages = []

    for bus in bus_names:
        dss.Circuit.SetActiveBus(bus)
        data = dss.Bus.puVmagAngle()

        for magnitude in data[0::2]:
            if magnitude > 0.01:
                voltages.append(float(magnitude))

    print("Circuit:", dss.Circuit.Name())
    print("Converged:", dss.Solution.Converged())
    print("Bus count:", len(bus_names))
    print(
        "Configured load (kW):",
        sum(p for p, q in BUS_LOADS.values()),
    )
    print(
        "Configured load (kvar):",
        sum(q for p, q in BUS_LOADS.values()),
    )

    if not voltages:
        raise RuntimeError(
            "Zero bus voltages persist. Do not use these electrical results."
        )

    losses = dss.Circuit.Losses()
    thermal = analyze_thermal_limits(ampacity_ratings_a={})

    print("\nThermal analysis")
    print("Thermal status:", thermal["thermal_status"])
    print("Branches measured:", thermal["branch_count"])

    for result in thermal["results"]:
        print(
            f"{result.branch_id}: "
            f"current={result.measured_current_a:.3f} A, "
            f"status={result.status}"
        )

    results = {
        "converged": True,
        "bus_count": len(bus_names),
        "energized_bus_nodes": len(voltages),
        "min_voltage_pu": min(voltages),
        "max_voltage_pu": max(voltages),
        "real_losses_kw": losses[0] / 1000,
        "reactive_losses_kvar": losses[1] / 1000,
    }

    print("\nIEEE 33-bus results")
    for key, value in results.items():
        if isinstance(value, float):
            print(f"{key}: {value:.6f}")
        else:
            print(f"{key}: {value}")

    return results


if __name__ == "__main__":
    print("Solving IEEE 33-bus feeder...")
    solve_ieee33()
