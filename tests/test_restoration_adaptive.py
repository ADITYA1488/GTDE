from types import SimpleNamespace

from src.ieee33_network import build_ieee33_network
from src.restoration_reporting import is_fully_verified
import src.restoration_powerflow as restoration_powerflow


def test_adaptive_feedback_uses_electrical_checks_when_thermal_is_unassessed(
    monkeypatch,
):
    net = build_ieee33_network()
    supplied_buses = sorted(net.buses)
    plans = [
        SimpleNamespace(
            close_ties=[tie_id],
            open_branches=[],
            restored_kw=500.0,
            restoration_pct=100.0,
            switching_operations=operations,
            supplied_buses=supplied_buses,
            valid=True,
            estimated_loss_kw=loss_proxy,
        )
        for tie_id, operations, loss_proxy in (
            ("T33", 1, 300.0),
            ("T34", 2, 200.0),
            ("T35", 3, 100.0),
            ("T36", 4, 40.0),
            ("T37", 5, 30.0),
        )
    ]
    monkeypatch.setattr(
        restoration_powerflow,
        "find_restoration_plans",
        lambda *args, **kwargs: plans,
    )
    monkeypatch.setattr(
        restoration_powerflow,
        "evaluate_ieee33_configuration",
        lambda **kwargs: {
            "converged": True,
            "voltage_feasible": True,
            "min_voltage_pu": 0.96,
            "max_voltage_pu": 1.0,
            "real_losses_kw": 10.0,
            "energized_phase_nodes": 99,
            "energized_buses": supplied_buses,
            "thermal_status": "UNASSESSED",
        },
    )

    def evaluated_order(strategy):
        order = []
        results = restoration_powerflow.evaluate_restoration_plans(
            net,
            max_results=4,
            max_electrical_evaluations=4,
            strategy=strategy,
            progress_callback=(
                lambda completed, total, result:
                    order.append(result.plan.close_ties[0])
            ),
        )
        assert len(results) == 4
        assert all(result.thermal_status == "UNASSESSED" for result in results)
        assert all(
            "Thermal limits unverified." in result.rejection_reason
            for result in results
        )
        assert all(result.graph_electrical_consistent is True for result in results)
        assert all(not is_fully_verified(result) for result in results)
        return order

    assert evaluated_order("baseline") == ["T33", "T34", "T35", "T36"]
    assert evaluated_order("adaptive") == ["T33", "T34", "T35", "T37"]
