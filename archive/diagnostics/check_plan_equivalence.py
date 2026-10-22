from src.restoration_powerflow import evaluate_ieee33_configuration

plans = [
    (["T35"], ["L08"]),
    (["T35"], ["L08", "L16"]),
    (["T35"], ["L08", "L17"]),
]

for ties, opened in plans:
    result = evaluate_ieee33_configuration(
        closed_ties=ties,
        opened_branches=opened,
        faulted_branches=["L15"],
        capacitor_bus=33,
        capacitor_kvar=1500,
    )
    print("Result keys:", list(result.keys()))
    print("Full result:", result)

    print(f"\nTies: {ties}, opened: {opened}")
    print("Converged:", result.get("converged"))
    print("Voltage feasible:", result["voltage_feasible"])
    print("Energized buses:", result.get("energized_buses"))
    print("Minimum voltage:", result.get("min_voltage_pu"))
    print("Maximum voltage:", result.get("max_voltage_pu"))
    print("Real power losses (kW):", result.get("losses_kw"))
    print("Restored load (kW):", result.get("restored_kw"))
    print("Thermal status:", result["thermal_status"])