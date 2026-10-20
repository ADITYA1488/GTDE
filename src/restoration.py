
from itertools import combinations
import networkx as nx

# Keep your existing RestorationPlan import or definition.
# If RestorationPlan is defined in this file already, retain that definition.
from dataclasses import dataclass, field


@dataclass
class RestorationPlan:
    close_ties: list
    open_branches: list
    restored_kw: float
    restoration_pct: float
    switching_operations: int
    supplied_buses: list
    valid: bool
    errors: list = field(default_factory=list)
    estimated_loss_kw: float = 0.0
    score: float = 0.0

def _loss_proxy(net, graph):
    """Graph-ranking proxy only; NOT physical electrical losses."""
    supplied = net.supplied_buses(graph)
    tree = graph.subgraph(supplied)
    total = 0.0

    for u, v, data in tree.edges(data=True):
        temp = nx.Graph(tree)
        temp.remove_edge(u, v)

        source_side = nx.node_connected_component(temp, net.source_bus)
        other_side = set(temp.nodes()) - source_side
        load = sum(
            float(net.buses[n].get("load_kw", 0))
            for n in other_side
        )
        resistance = float(data.get("resistance_ohm", 0.2))
        total += resistance * (load / 1000) ** 2

    return round(total, 6)


def find_restoration_plans(
    net, faulted_branches=None, max_operations=3, max_results=10
):
    faulted = set(faulted_branches or [])

    if max_operations < 0:
        raise ValueError("max_operations must be non-negative")
    if max_results < 1:
        return []

    ties = [
        b.branch_id for b in net.branches
        if not b.normally_closed and b.branch_id not in faulted
    ]
    lines = [
        b.branch_id for b in net.branches
        if b.normally_closed and b.switchable
        and b.branch_id not in faulted
    ]

    total_load = net.total_load_kw()
    plans = []

    for nc in range(min(len(ties), max_operations) + 1):
        for close in combinations(ties, nc):
            budget = max_operations - nc

            for no in range(min(len(lines), budget) + 1):
                for opened in combinations(lines, no):
                    # Validate first: avoid expensive loss calculations
                    # for cyclic or otherwise invalid configurations.
                    errors = net.validate_topology(close, opened, faulted)
                    graph = net.build_graph(close, opened, faulted)

                    if errors:
                        restored = net.restored_load_kw(graph)
                        pct = 100 * restored / total_load if total_load else 100
                        proxy = float("inf")
                    else:
                        restored = net.restored_load_kw(graph)
                        pct = 100 * restored / total_load if total_load else 100
                        proxy = _loss_proxy(net, graph)

                    operations = nc + no
                    score = pct - operations * 1.5 - (
                        proxy * 0.01 if proxy != float("inf") else 1e9
                    )

                    plans.append(RestorationPlan(
                        close_ties=list(close),
                        open_branches=list(opened),
                        restored_kw=round(restored, 3),
                        restoration_pct=round(pct, 2),
                        switching_operations=operations,
                        supplied_buses=sorted(net.supplied_buses(graph)),
                        valid=not errors,
                        errors=errors,
                        estimated_loss_kw=proxy,
                        score=round(score, 4),
                    ))

    plans.sort(key=lambda p: (
        not p.valid,
        -p.restored_kw,
        p.switching_operations,
        p.estimated_loss_kw,
    ))
    return plans[:max_results]
