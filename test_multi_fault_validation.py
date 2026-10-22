
import pytest

from src.ieee33_network import build_ieee33_network
from src.restoration_powerflow import evaluate_restoration_plans


@pytest.mark.parametrize(
    "faulted_branch",
    ["L05", "L10", "L17", "L25", "L32"],
)
def test_restoration_across_multiple_faults(faulted_branch):
    net = build_ieee33_network()

    results = evaluate_restoration_plans(
        net,
        faulted_branches={faulted_branch},
        max_operations=3,
        max_results=5,
        capacitor_bus=33,
        capacitor_kvar=900,
        max_electrical_evaluations=10,
        strategy="adaptive",
    )

    assert results, f"No candidates returned for fault {faulted_branch}"

    for result in results:
        assert result.plan.valid
        assert faulted_branch not in result.plan.close_ties
        assert faulted_branch not in result.plan.open_branches
        assert result.thermal_status == "UNASSESSED"

        if result.converged:
            assert result.graph_electrical_consistent == (
                result.graph_supplied_buses
                == result.electrically_energized_buses
            )

        if result.voltage_feasible:
            assert result.converged
            assert result.graph_electrical_consistent
            assert result.min_voltage_pu >= 0.95
            assert result.max_voltage_pu <= 1.05
