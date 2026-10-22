
from src.ieee33_network import build_ieee33_network
from src.restoration_powerflow import evaluate_restoration_plans


def test_restoration_plans_are_evaluated_electrically():
    net = build_ieee33_network()

    results = evaluate_restoration_plans(
        net,
        faulted_branches={"L10"},
        max_operations=2,
        max_results=5,
        capacitor_bus=33,
        capacitor_kvar=900,
    )

    assert results, "No restoration candidates were returned."

    for result in results:
        assert result.plan.valid
        assert "L10" not in result.plan.close_ties
        assert "L10" not in result.plan.open_branches
        assert result.thermal_status == "UNASSESSED"

        if result.converged:
            assert result.graph_electrical_consistent == (
                result.graph_supplied_buses
                == result.electrically_energized_buses
            )

        if result.graph_electrical_consistent:
            assert result.rejection_reason != (
                "Power flow did not converge."
            )

    print("\nTop restoration candidates:")

    for index, result in enumerate(results, start=1):
        print(f"\nCandidate {index}")
        print(f"  Close ties: {result.plan.close_ties}")
        print(f"  Open branches: {result.plan.open_branches}")
        print(f"  Restored load: {result.plan.restored_kw:.1f} kW")
        print(f"  Restoration: {result.plan.restoration_pct:.2f}%")
        print(f"  Converged: {result.converged}")
        print(f"  Voltage feasible: {result.voltage_feasible}")
        print(f"  Minimum voltage: {result.min_voltage_pu}")
        print(f"  Maximum voltage: {result.max_voltage_pu}")
        print(f"  Real losses: {result.real_losses_kw}")
        print(
            "  Graph/OpenDSS consistent:",
            result.graph_electrical_consistent,
        )
        print("  Graph buses:", result.graph_supplied_buses)
        print(
            "  OpenDSS buses:",
            result.electrically_energized_buses,
        )
        print("  Thermal status:", result.thermal_status)
        print("  Rejection reason:", result.rejection_reason)


if __name__ == "__main__":
    test_restoration_plans_are_evaluated_electrically()
    print("\nPASS: Restoration integration test.")
