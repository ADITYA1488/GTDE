import opendssdirect as dss
from src.ieee33_powerflow import build_ieee33_circuit

plans = [
    (["T35"], ["L08"]),
    (["T35"], ["L08", "L16"]),
    (["T35"], ["L08", "L17"]),
]

for ties, opened in plans:
    build_ieee33_circuit(
        closed_ties=ties,
        opened_branches=opened,
        faulted_branches=["L15"],
        capacitor_bus=33,
        capacitor_kvar=1500,
    )

    dss.Text.Command("Set Mode=Snapshot")
    dss.Text.Command("Solve")

    print(f"\nRequested ties={ties}, opened={opened}")
    for branch in ["L08", "L15", "L16", "L17", "T35"]:
        dss.Circuit.SetActiveElement(f"Line.{branch}")
        print(f"  {branch}: enabled={dss.CktElement.Enabled()}")
    print(f"  Converged={dss.Solution.Converged()}")
    print(f"  Losses kW={dss.Circuit.Losses()[0] / 1000:.6f}")
