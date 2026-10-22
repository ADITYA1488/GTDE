from src.ieee33_powerflow import evaluate_ieee33_configuration

result = evaluate_ieee33_configuration(
    closed_ties={"T35"},
    opened_branches=set(),
    faulted_branches={"L10"},
    capacitor_bus=33,
    capacitor_kvar=900,
)

for key, value in result.items():
    print(f"{key}: {value}")

assert result["converged"] is True
assert result["voltage_feasible"] is True
assert abs(result["min_voltage_pu"] - 0.951278) < 0.00001
assert abs(result["real_losses_kw"] - 117.121) < 0.01

print("\nPASS: Capacitor-supported evaluator regression test.")