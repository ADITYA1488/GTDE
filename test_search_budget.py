
import pytest

from src.ieee33_network import build_ieee33_network
from src.restoration_powerflow import evaluate_restoration_plans


def test_electrical_evaluation_budget_limits_results():
    net = build_ieee33_network()

    results = evaluate_restoration_plans(
        net,
        faulted_branches={"L10"},
        max_operations=2,
        max_results=10,
        capacitor_bus=33,
        capacitor_kvar=900,
        max_electrical_evaluations=3,
    )

    assert len(results) <= 3
    assert all(result.plan.valid for result in results)


@pytest.mark.parametrize("budget", [0, -1, 1.5, True])
def test_invalid_electrical_evaluation_budget_is_rejected(budget):
    net = build_ieee33_network()

    with pytest.raises(ValueError):
        evaluate_restoration_plans(
            net,
            faulted_branches={"L10"},
            max_electrical_evaluations=budget,
        )
