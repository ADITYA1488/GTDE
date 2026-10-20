
from dataclasses import dataclass

from src.restoration import find_restoration_plans
from src.ieee33_powerflow import evaluate_ieee33_configuration


@dataclass
class ElectricalRestorationResult:
    plan: object
    converged: bool
    voltage_feasible: bool
    min_voltage_pu: float | None
    max_voltage_pu: float | None
    real_losses_kw: float | None
    energized_phase_nodes: int
    thermal_status: str
    graph_electrical_consistent: bool
    graph_supplied_buses: list
    electrically_energized_buses: list
    rejection_reason: str | None = None


def evaluate_restoration_plans(
    net,
    faulted_branches=None,
    max_operations=3,
    max_results=10,
    capacitor_bus=None,
    capacitor_kvar=0,
    max_electrical_evaluations=100,
):
    """Rank graph candidates, then electrically evaluate a bounded shortlist.

    The shortlist is heuristic: it does not guarantee the globally best
    electrical solution. Thermal compliance remains unassessed unless
    verified ampacity ratings are supplied through a separate analysis.
    """
    if max_results < 1:
        return []

    if (
        not isinstance(max_electrical_evaluations, int)
        or isinstance(max_electrical_evaluations, bool)
        or max_electrical_evaluations < 1
    ):
        raise ValueError(
            "max_electrical_evaluations must be a positive integer."
        )

    faulted = set(faulted_branches or [])

    # Generate graph candidates. The existing search enumerates candidates
    # and ranks them using restored load, switching operations and its
    # graph-based loss proxy; that proxy is not a physical loss calculation.
    plans = find_restoration_plans(
        net,
        faulted_branches=faulted,
        max_operations=max_operations,
        max_results=10**9,
    )

    graph_candidates = [plan for plan in plans if plan.valid]

    # Rank before applying the electrical simulation budget.
    graph_candidates.sort(
        key=lambda plan: (
            -plan.restored_kw,
            plan.switching_operations,
            (
                plan.estimated_loss_kw
                if plan.estimated_loss_kw is not None
                else float("inf")
            ),
            tuple(plan.close_ties),
            tuple(plan.open_branches),
        )
    )

    shortlist = graph_candidates[:max_electrical_evaluations]
    results = []

    for plan in shortlist:
        graph_buses = sorted(set(plan.supplied_buses))

        try:
            electrical = evaluate_ieee33_configuration(
                closed_ties=set(plan.close_ties),
                opened_branches=set(plan.open_branches),
                faulted_branches=faulted,
                capacitor_bus=capacitor_bus,
                capacitor_kvar=capacitor_kvar,
            )
        except Exception as exc:
            results.append(
                ElectricalRestorationResult(
                    plan=plan,
                    converged=False,
                    voltage_feasible=False,
                    min_voltage_pu=None,
                    max_voltage_pu=None,
                    real_losses_kw=None,
                    energized_phase_nodes=0,
                    thermal_status="UNASSESSED",
                    graph_electrical_consistent=False,
                    graph_supplied_buses=graph_buses,
                    electrically_energized_buses=[],
                    rejection_reason=f"Power-flow evaluation failed: {exc}",
                )
            )
            continue

        converged = electrical["converged"]
        voltage_feasible = electrical["voltage_feasible"]
        electrical_buses = sorted(
            set(electrical.get("energized_buses", []))
        )

        consistent = converged and graph_buses == electrical_buses

        if not converged:
            reason = "Power flow did not converge."
        elif not consistent:
            graph_only = sorted(set(graph_buses) - set(electrical_buses))
            electrical_only = sorted(
                set(electrical_buses) - set(graph_buses)
            )
            reason = (
                "Graph/OpenDSS energized-bus mismatch: "
                f"graph-only={graph_only}, "
                f"electrical-only={electrical_only}"
            )
        elif not voltage_feasible:
            reason = "Voltage limits violated."
        else:
            reason = None

        results.append(
            ElectricalRestorationResult(
                plan=plan,
                converged=converged,
                voltage_feasible=voltage_feasible,
                min_voltage_pu=electrical["min_voltage_pu"],
                max_voltage_pu=electrical["max_voltage_pu"],
                real_losses_kw=electrical["real_losses_kw"],
                energized_phase_nodes=electrical[
                    "energized_phase_nodes"
                ],
                thermal_status=electrical["thermal_status"],
                graph_electrical_consistent=consistent,
                graph_supplied_buses=graph_buses,
                electrically_energized_buses=electrical_buses,
                rejection_reason=reason,
            )
        )

    # Electrically acceptable candidates rank first. Among them, prioritize
    # restored load, then actual OpenDSS losses and switching operations.
    results.sort(
        key=lambda item: (
            not (
                item.converged
                and item.voltage_feasible
                and item.graph_electrical_consistent
            ),
            -item.plan.restored_kw,
            (
                item.real_losses_kw
                if item.real_losses_kw is not None
                else float("inf")
            ),
            item.plan.switching_operations,
        )
    )

    return results[:max_results]
