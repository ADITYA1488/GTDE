from src.demo_network import build_demo_network
from src.powerflow import evaluate_power_flow


def test_t25_powerflow_converges():
    net = build_demo_network()

    result = evaluate_power_flow(
        net,
        closed_ties={"T25"},
        faulted_branches={"L45"},
    )

    assert result["converged"], result.get("error")
    assert result["unsupplied_load_kw"] == 0


def test_candidate_voltage_limits():
    net = build_demo_network()

    for tie in ["T25", "T36", "T46"]:
        result = evaluate_power_flow(
            net,
            closed_ties={tie},
            faulted_branches={"L45"},
        )

        assert result["converged"], f"{tie}: {result.get('error')}"

        vmin = result["minimum_bus_voltage_pu"]
        vmax = result["maximum_bus_voltage_pu"]

        assert vmin is not None and vmin >= 0.95, tie
        assert vmax is not None and vmax <= 1.05, tie


def test_real_losses_are_nonnegative():
    net = build_demo_network()

    for tie in ["T25", "T36", "T46"]:
        result = evaluate_power_flow(
            net,
            closed_ties={tie},
            faulted_branches={"L45"},
        )

        assert result["converged"], result.get("error")
        assert result["real_losses_kw"] >= 0