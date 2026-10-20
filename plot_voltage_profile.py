
import csv
from pathlib import Path

import matplotlib.pyplot as plt
from opendssdirect import dss

from src.ieee33_powerflow import build_ieee33_circuit

ROOT = Path(__file__).resolve().parent
RESULTS = ROOT / "results"
RESULTS.mkdir(exist_ok=True)


def main():
    # Build and solve using the same circuit definition as the existing solver.
    build_ieee33_circuit()
    dss.Text.Command("Set Mode=Snapshot")
    dss.Text.Command("Solve")

    if not dss.Solution.Converged():
        raise RuntimeError("OpenDSS power flow did not converge.")

    bus_voltages = []

    for bus_name in dss.Circuit.AllBusNames():
        dss.Circuit.SetActiveBus(bus_name)
        bus_data = dss.Bus.puVmagAngle()

        # puVmagAngle contains alternating magnitude and angle values.
        magnitudes = [
            float(value)
            for value in bus_data[0::2]
            if value > 0.01
        ]

        if magnitudes:
            # Record the minimum phase voltage at each bus.
            bus_voltages.append(
                (bus_name, min(magnitudes))
            )

    if not bus_voltages:
        raise RuntimeError("No energized bus voltages were returned.")

    # Sort numerically by bus number, not alphabetically.
    bus_voltages.sort(
        key=lambda item: int(
            "".join(ch for ch in item[0] if ch.isdigit())
        )
    )

    csv_path = RESULTS / "ieee33_bus_voltages.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        writer.writerow(["bus", "minimum_phase_voltage_pu"])
        writer.writerows(bus_voltages)

    bus_numbers = [
        int("".join(ch for ch in name if ch.isdigit()))
        for name, _ in bus_voltages
    ]
    voltages = [value for _, value in bus_voltages]

    plt.figure(figsize=(12, 6))
    plt.plot(bus_numbers, voltages, marker="o", linewidth=1.8)
    plt.axhline(0.95, linestyle="--", label="0.95 pu reference")
    plt.axhline(1.05, linestyle="--", label="1.05 pu reference")
    plt.xlabel("Bus number")
    plt.ylabel("Minimum phase voltage (pu)")
    plt.title("IEEE 33-Bus Feeder: Voltage Profile")
    plt.xticks(range(1, 34))
    plt.grid(True, alpha=0.3)
    plt.legend()
    plt.tight_layout()

    plot_path = RESULTS / "ieee33_voltage_profile.png"
    plt.savefig(plot_path, dpi=200)
    plt.close()

    print(f"Converged: {dss.Solution.Converged()}")
    print(f"Buses plotted: {len(bus_voltages)}")
    print(f"Minimum plotted voltage: {min(voltages):.6f} pu")
    print(f"Maximum plotted voltage: {max(voltages):.6f} pu")
    print(f"CSV saved: {csv_path}")
    print(f"Plot saved: {plot_path}")


if __name__ == "__main__":
    main()
