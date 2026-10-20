
from opendssdirect import dss

from src.ieee33_electrical_data import (
    BASE_KV,
    SOURCE_BUS,
    MAIN_BRANCHES,
    TIE_BRANCHES,
    BUS_LOADS,
)


def build_ieee33_circuit():
    dss.Text.Command("Clear")
    dss.Text.Command("Set DefaultBaseFrequency=50")

    dss.Text.Command(
        f"New Circuit.IEEE33 "
        f"bus1=Bus{SOURCE_BUS} "
        f"phases=3 basekV={BASE_KV} pu=1.0 "
        f"frequency=50"
    )

    for i, (u, v, r, x) in enumerate(MAIN_BRANCHES, start=1):
        dss.Text.Command(
            f"New Line.L{i:02d} "
            f"bus1=Bus{u}.1.2.3 bus2=Bus{v}.1.2.3 "
            f"phases=3 r1={r} x1={x} "
            f"r0={3*r} x0={3*x} length=1 units=km"
        )

    for i, (u, v, r, x) in enumerate(TIE_BRANCHES, start=33):
        dss.Text.Command(
            f"New Line.T{i} "
            f"bus1=Bus{u}.1.2.3 bus2=Bus{v}.1.2.3 "
            f"phases=3 r1={r} x1={x} "
            f"r0={3*r} x0={3*x} length=1 units=km "
            f"enabled=no"
        )

    for bus, (p_kw, q_kvar) in BUS_LOADS.items():
        if bus == SOURCE_BUS or (p_kw == 0 and q_kvar == 0):
            continue

        dss.Text.Command(
            f"New Load.Load{bus} "
            f"bus1=Bus{bus}.1.2.3 phases=3 conn=wye "
            f"model=1 kV={BASE_KV} "
            f"kW={p_kw} kvar={q_kvar}"
        )

    dss.Text.Command(f"Set VoltageBases=[{BASE_KV}]")
    dss.Text.Command("CalcVoltageBases")


def solve_ieee33():
    build_ieee33_circuit()

    # Explicitly solve using OpenDSS commands.
    dss.Text.Command("Set Mode=Snapshot")
    dss.Text.Command("Solve")

    if not dss.Solution.Converged():
        raise RuntimeError("OpenDSS power flow failed to converge.")

    bus_names = list(dss.Circuit.AllBusNames())
    voltages = []

    for bus in bus_names:
        dss.Circuit.SetActiveBus(bus)
        data = dss.Bus.puVmagAngle()

        # Magnitude, angle, magnitude, angle, ...
        for magnitude in data[0::2]:
            if magnitude > 0.01:
                voltages.append(float(magnitude))

    print("Circuit:", dss.Circuit.Name())
    print("Converged:", dss.Solution.Converged())
    print("Bus count:", len(bus_names))
    print("Configured load (kW):", sum(p for p, q in BUS_LOADS.values()))
    print("Configured load (kvar):", sum(q for p, q in BUS_LOADS.values()))

    if not voltages:
        print("Source voltage PU:", dss.Vsources.PU())
        print("Source base kV:", dss.Vsources.BasekV())
        print("Circuit power:", dss.Circuit.TotalPower())
        print("Circuit losses:", dss.Circuit.Losses())
        raise RuntimeError(
            "Zero bus voltages persist. Do not use these electrical results."
        )

    losses = dss.Circuit.Losses()

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
        print(f"{key}: {value:.6f}" if isinstance(value, float)
              else f"{key}: {value}")

    return results


if __name__ == "__main__":
    print("Solving IEEE 33-bus feeder...")
    solve_ieee33()
