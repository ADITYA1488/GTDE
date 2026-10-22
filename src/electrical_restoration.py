
"""Evaluate graph-generated restoration plans using OpenDSS."""

from src.ieee33_powerflow import evaluate_ieee33_configuration


VOLTAGE_MIN_PU = 0.95
VOLTAGE_MAX_PU = 1.05


def evaluate_restoration_plan(plan, faulted_branches=()):
    """Combine graph validity with electrical feasibility.

    A graph-valid plan is not automatically electrically feasible.
    This function verifies the proposed switching state with OpenDSS.
    """
    if not plan.valid:
        return {
            "graph_valid": False,
            "powerflow_converged": False,
            "voltage_feasible": False,
            "electrically_feasible": False,
            "restored_kw": plan.restored_kw,
            "switching_operations": plan.switching_operations,
            "real_losses_kw": None,
            "min_voltage_pu": None,
            "max_voltage_pu": None,
            "notes": "; ".join(plan.errors) or "Invalid graph topology",
        }

    electrical = evaluate_ieee33_configuration(
        closed_ties=plan.close_ties,
        opened_branches=plan.open_branches,
        faulted_branches=faulted_branches,
    )

    converged = electrical["converged"]
    min_v = electrical["min_voltage_pu"]
    max_v = electrical["max_voltage_pu"]

    voltage_ok = (
        converged
        and min_v is not None
        and max_v is not None
        and VOLTAGE_MIN_PU <= min_v
        and max_v <= VOLTAGE_MAX_PU
    )

    return {
        "graph_valid": True,
        "powerflow_converged": converged,
        "voltage_feasible": voltage_ok,
        "electrically_feasible": voltage_ok,
        "restored_kw": plan.restored_kw,
        "switching_operations": plan.switching_operations,
        "real_losses_kw": electrical["real_losses_kw"],
        "min_voltage_pu": min_v,
        "max_voltage_pu": max_v,
        "thermal_status": electrical["thermal_status"],
        "notes": (
            "Voltage limits satisfied"
            if voltage_ok
            else "Power flow failed or voltage limits violated"
        ),
    }
