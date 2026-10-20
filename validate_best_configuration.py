from src.ieee33_network import build_ieee33_network
from benchmark_combined_optimization import evaluate_configuration


def main():
    net = build_ieee33_network()

    result = evaluate_configuration(
        net,
        closed_ties=["T35"],
        opened_branches=["L10"],
        capacitor_bus=33,
        capacitor_kvar=900,
    )

    print("\nGTDE — Best Configuration Validation")
    print("-" * 45)
    print(f"Configuration: {result['configuration']}")
    print(f"Topology valid: {result['topology_valid']}")
    print(f"Power flow converged: {result['powerflow_converged']}")
    print(f"Feasible: {result['feasible']}")
    print(f"Minimum voltage: {result.get('min_voltage_pu', float('nan')):.6f} pu")
    print(f"Maximum voltage: {result.get('max_voltage_pu', float('nan')):.6f} pu")
    print(f"Real losses: {result.get('real_losses_kw', float('nan')):.3f} kW")
    print(f"Load served: {result['load_served_pct']:.3f}%")
    print(f"Notes: {result['feasibility_notes']}")

    if not result["feasible"]:
        raise SystemExit("FAIL: The selected configuration is not feasible.")

    if abs(result["min_voltage_pu"] - 0.951278) > 0.002:
        raise SystemExit("FAIL: Minimum voltage differs from the benchmark.")

    if abs(result["real_losses_kw"] - 117.121) > 1.0:
        raise SystemExit("FAIL: Real losses differ from the benchmark.")

    print("\nPASS: The selected configuration reproduced the expected results.")


if __name__ == "__main__":
    main()