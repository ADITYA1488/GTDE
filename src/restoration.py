
from itertools import combinations
from dataclasses import dataclass, field

import networkx as nx


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
    """Calculate a graph-ranking proxy, NOT physical electrical losses.

    For a valid radial, source-connected graph, root the tree at the source.
    Calculate downstream load once per node instead of copying the graph
    and performing a connectivity search for every edge.

    Complexity: O(V + E) for a tree.
    """
    supplied = net.supplied_buses(graph)

    if not supplied or net.source_bus not in supplied:
        return 0.0

    tree = graph.subgraph(supplied)

    if tree.number_of_edges() == 0:
        return 0.0

    # This proxy assumes the supplied network is radial.
    if not nx.is_tree(tree):
        raise ValueError(
            "The loss proxy requires a connected radial supplied network."
        )

    source = net.source_bus

    # Build a rooted traversal of the tree.
    order = list(nx.dfs_preorder_nodes(tree, source))
    parents = dict(nx.dfs_predecessors(tree, source))

    # Start with the load at each node.
    subtree_load = {
        node: float(net.buses[node].get("load_kw", 0.0))
        for node in order
    }

    # Accumulate each child's downstream load into its parent.
    for node in reversed(order):
        parent = parents.get(node)
        if parent is not None:
            subtree_load[parent] += subtree_load[node]

    # Each parent-child edge carries the load in the child's subtree.
    total = 0.0

    for node, parent in parents.items():
        edge_data = tree[parent][node]
        resistance = float(edge_data.get("resistance_ohm", 0.2))
        downstream_load_mw = subtree_load[node] / 1000.0

        total += resistance * downstream_load_mw**2

    return round(total, 6)


def find_restoration_plans(
    net,
    faulted_branches=None,
    max_operations=3,
    max_results=10,
):
    """Enumerate, validate and rank graph-based restoration plans.

    Ranking prioritizes valid plans, restored load, fewer switching
    operations, and then the graph-based loss proxy.

    The proxy is not a substitute for OpenDSS power-flow analysis.
    """
    faulted = set(faulted_branches or [])

    if max_operations < 0:
        raise ValueError("max_operations must be non-negative")

    if max_results < 1:
        return []

    ties = [
        branch.branch_id
        for branch in net.branches
        if not branch.normally_closed
        and branch.branch_id not in faulted
    ]

    lines = [
        branch.branch_id
        for branch in net.branches
        if branch.normally_closed
        and branch.switchable
        and branch.branch_id not in faulted
    ]

    total_load = net.total_load_kw()
    plans = []

    for number_closed in range(
        min(len(ties), max_operations) + 1
    ):
        for close in combinations(ties, number_closed):
            remaining_budget = max_operations - number_closed

            for number_opened in range(
                min(len(lines), remaining_budget) + 1
            ):
                for opened in combinations(lines, number_opened):
                    # Validate topology before computing the loss proxy.
                    errors = net.validate_topology(
                        close, opened, faulted
                    )
                    graph = net.build_graph(
                        close, opened, faulted
                    )

                    # Determine source-connected buses once per candidate.
                    supplied = sorted(net.supplied_buses(graph))

                    restored = sum(
                        float(net.buses[bus].get("load_kw", 0.0))
                        for bus in supplied
                    )

                    pct = (
                        100.0 * restored / total_load
                        if total_load
                        else 100.0
                    )

                    if errors:
                        proxy = float("inf")
                    else:
                        proxy = _loss_proxy(net, graph)

                    operations = number_closed + number_opened

                    score = pct - operations * 1.5 - (
                        proxy * 0.01
                        if proxy != float("inf")
                        else 1e9
                    )

                    plans.append(
                        RestorationPlan(
                            close_ties=list(close),
                            open_branches=list(opened),
                            restored_kw=round(restored, 3),
                            restoration_pct=round(pct, 2),
                            switching_operations=operations,
                            supplied_buses=supplied,
                            valid=not errors,
                            errors=errors,
                            estimated_loss_kw=proxy,
                            score=round(score, 4),
                        )
                    )

    plans.sort(
        key=lambda plan: (
            not plan.valid,
            -plan.restored_kw,
            plan.switching_operations,
            plan.estimated_loss_kw,
        )
    )

    return plans[:max_results]
