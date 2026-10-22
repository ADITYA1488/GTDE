
from src.ieee33_powerflow import (
    build_ieee33_circuit,
)
from opendssdirect import dss


def main():
    build_ieee33_circuit(
        closed_ties={"T35"},
        opened_branches={"L10"},
    )

    # Apply the same capacitor used by the benchmark.
    dss.Text.Command(
        "New Capacitor.Support "
        "bus1=Bus33.1.2.3 "
        "phases=3 conn=wye "
        "kV=12.66 kvar=900"
    )

    dss.Text.Command("Set Mode=Snapshot")
    dss.Text.Command("Solve")

    if not dss.Solution.Converged():
        raise RuntimeError("Power flow did not converge.")

    voltages = []

    for bus in dss.Circuit.AllBusNames():
        dss.Circuit.SetActiveBus(bus)
        values = dss.Bus.puVmagAngle()

        voltages.extend(
            float(v)
            for v in values[0::2]
            if v > 0.01
        )

    losses = dss.Circuit.Losses()

    print("Converged:", dss.Solution.Converged())
    print("Minimum voltage:", min(voltages))
    print("Maximum voltage:", max(voltages))
    print("Real losses (kW):", losses[0] / 1000)
    print(
        "Voltage feasible:",
        min(voltages) >= 0.95 and max(voltages) <= 1.05,
    )


if __name__ == "__main__":
    main()
