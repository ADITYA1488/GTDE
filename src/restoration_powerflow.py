"""Bounded graph-based restoration search with OpenDSS validation."""
from dataclasses import dataclass
from typing import Callable

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
    rejection_reason: str | None = None
    graph_electrical_consistent: bool = False
    graph_supplied_buses: list | None = None
    electrically_energized_buses: list | None = None
    solver_diagnostic: str | None = None


def evaluate_restoration_plans(
    net,
    faulted_branches=None,
    max_operations=3,
    max_results=10,
    capacitor_bus=None,
    capacitor_kvar=0,
    max_electrical_evaluations=10,
    strategy="adaptive",
    progress_callback: Callable | None = None,
    ampacity_ratings_a=None,
):
    """Search a bounded candidate set and validate candidates with OpenDSS.

    The graph search retains only a bounded number of plans in memory. The
    electrical budget independently limits OpenDSS solves. Callback signature:
    ``progress_callback(completed, total, result)``.
    """
    for name, value, minimum in (
        ("max_results", max_results, 1),
        ("max_electrical_evaluations", max_electrical_evaluations, 1),
    ):
        if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
            raise ValueError(f"{name} must be an integer >= {minimum}.")
    if strategy not in {"baseline", "adaptive"}:
        raise ValueError("strategy must be 'baseline' or 'adaptive'.")
    if isinstance(max_operations, bool) or not isinstance(max_operations, int) or max_operations < 0:
        raise ValueError("max_operations must be a non-negative integer.")

    faulted = set(faulted_branches or [])
    budget = max_electrical_evaluations
    # Generate a bounded shortlist, rather than asking the graph planner to
    # retain up to one billion plans. The multiplier gives adaptive search room
    # to explore beyond its initial candidates while bounding memory.
    candidate_limit = min(2000, max(max_results, budget * 50))
    plans = find_restoration_plans(
        net, faulted_branches=faulted, max_operations=max_operations,
        max_results=candidate_limit,
    )
    plans = [p for p in plans if p.valid]

    # Deduplicate plans that produce the exact same active-branch topology.
    # Keep the plan with fewer switching operations.
    def active_topology_key(plan):
        closed_ties = set(plan.close_ties)
        opened_branches = set(plan.open_branches)

        active = []
        for branch in net.branches:
            bid = branch.branch_id

            if bid in opened_branches or bid in faulted:
                continue

            if branch.normally_closed or bid in closed_ties:
                active.append(bid)

        return tuple(sorted(active))

    unique_plans = {}

    for plan in plans:
        key = active_topology_key(plan)
        existing = unique_plans.get(key)

        rank = (
            plan.switching_operations,
            plan.estimated_loss_kw,
            tuple(sorted(plan.close_ties)),
            tuple(sorted(plan.open_branches)),
        )

        if existing is None:
            unique_plans[key] = plan
        else:
            existing_rank = (
                existing.switching_operations,
                existing.estimated_loss_kw,
                tuple(sorted(existing.close_ties)),
                tuple(sorted(existing.open_branches)),
            )

            if rank < existing_rank:
                unique_plans[key] = plan

    plans = list(unique_plans.values())


    # Keep a shortlist spanning different tie-switch configurations.
    # This is a heuristic for candidate diversity, not an optimality guarantee.
    if plans:
        plans.sort(
            key=lambda p: (
                -p.restored_kw,
                p.switching_operations,
                p.estimated_loss_kw,
            )
        )

        groups = {}
        for plan in plans:
            key = tuple(sorted(plan.close_ties))
            groups.setdefault(key, []).append(plan)

        diverse = []
        group_keys = sorted(
            groups,
            key=lambda key: (
                -max(p.restored_kw for p in groups[key]),
                min(p.switching_operations for p in groups[key]),
                min(p.estimated_loss_kw for p in groups[key]),
                key,
            ),
        )

        # Round-robin across tie-switch groups so one group cannot
        # consume the entire electrical evaluation shortlist.
        depth = 0
        while len(diverse) < candidate_limit:
            added = False
            for key in group_keys:
                if depth < len(groups[key]):
                    diverse.append(groups[key][depth])
                    added = True
                    if len(diverse) >= candidate_limit:
                        break
            if not added:
                break
            depth += 1

        plans = diverse

    if not plans:
        if progress_callback:
            try:
                progress_callback(0, 0, None)
            except Exception:
                pass
        return []

    budget = min(budget, len(plans))
    completed = 0
    results = []
    evaluated = set()

    def evaluate_and_report(plan):
        nonlocal completed
        graph_buses = sorted(plan.supplied_buses)
        try:
            electrical = evaluate_ieee33_configuration(
                closed_ties=set(plan.close_ties),
                opened_branches=set(plan.open_branches),
                faulted_branches=faulted,
                capacitor_bus=capacitor_bus,
                capacitor_kvar=capacitor_kvar,
                ampacity_ratings_a=ampacity_ratings_a,
            )
            converged = bool(electrical.get("converged", False))
            voltage_feasible = bool(electrical.get("voltage_feasible", False))
            electrical_buses = sorted(set(electrical.get("energized_buses") or []))
            # Explicitly compare topology-derived energized buses with OpenDSS.
            graph_consistent = converged and graph_buses == electrical_buses
            reasons = []
            if not converged:
                reasons.append("Power flow did not converge.")
            if converged and not voltage_feasible:
                reasons.append("Voltage limits violated.")
            if converged and not graph_consistent:
                reasons.append("Graph and OpenDSS energized-bus sets disagree.")
            thermal_status = electrical.get("thermal_status", "UNASSESSED")
            if thermal_status == "VIOLATION":
                reasons.append("Branch ampacity limit violated.")
            result = ElectricalRestorationResult(
                plan=plan, converged=converged, voltage_feasible=voltage_feasible,
                min_voltage_pu=electrical.get("min_voltage_pu"),
                max_voltage_pu=electrical.get("max_voltage_pu"),
                real_losses_kw=electrical.get("real_losses_kw"),
                energized_phase_nodes=int(electrical.get("energized_phase_nodes", 0)),
                thermal_status=thermal_status, rejection_reason=" ".join(reasons) or None,
                graph_electrical_consistent=graph_consistent,
                graph_supplied_buses=graph_buses,
                electrically_energized_buses=electrical_buses,
                solver_diagnostic=electrical.get("solver_diagnostic"),
            )
            if not electrical["converged"]:
                reason = "Power flow did not converge."
            elif not electrical["voltage_feasible"]:
                reason = "Voltage limits violated."
            elif electrical["thermal_status"] == "VIOLATION":
                reason = "Branch ampacity limit violated."
            elif electrical["thermal_status"] == "UNASSESSED":
                reason = "Thermal limits unverified."
        except Exception as exc:
            result = ElectricalRestorationResult(
                plan=plan, converged=False, voltage_feasible=False,
                min_voltage_pu=None, max_voltage_pu=None, real_losses_kw=None,
                energized_phase_nodes=0, thermal_status="UNASSESSED",
                rejection_reason=f"Power-flow evaluation failed: {type(exc).__name__}: {exc}",
                graph_electrical_consistent=False,
                graph_supplied_buses=graph_buses,
                electrically_energized_buses=[],
            )
        completed += 1
        results.append(result)
        evaluated.add(tuple(sorted(plan.close_ties)) + ("|",) + tuple(sorted(plan.open_branches)))
        if progress_callback:
            try:
                progress_callback(completed, budget, result)
            except Exception:
                pass
        return result

    def candidate_key(plan):
        return (-plan.restored_kw, plan.switching_operations, plan.estimated_loss_kw)

    plans.sort(key=candidate_key)
    if strategy == "baseline":
        for plan in plans[:budget]:
            evaluate_and_report(plan)
    else:
        # Evaluate a small initial batch, then use actual OpenDSS results to
        # guide selection while preserving deterministic tie-breaks.
        for plan in plans[:min(3, budget)]:
            evaluate_and_report(plan)
        while completed < budget:
            remaining = [p for p in plans if (
                tuple(sorted(p.close_ties)) + ("|",) + tuple(sorted(p.open_branches))
            ) not in evaluated]
            if not remaining:
                break
            feasible = [
                r for r in results
                if r.converged
                   and r.voltage_feasible
                   and r.graph_electrical_consistent
                   and r.thermal_status == "PASS"
            ]
            if feasible:
                best_load = max(r.plan.restored_kw for r in feasible)
                remaining.sort(key=lambda p: (
                    p.restored_kw < best_load,
                    -p.restored_kw,
                    p.estimated_loss_kw,
                    p.switching_operations,
                ))
            evaluate_and_report(remaining[0])

    results.sort(key=lambda r: (
        not (
                r.converged
                and r.voltage_feasible
                and r.graph_electrical_consistent
                and r.thermal_status == "PASS"
        ),
        -r.plan.restored_kw,
        r.real_losses_kw if r.real_losses_kw is not None else float("inf"),
        r.plan.switching_operations,
    ))
    return results[:max_results]
