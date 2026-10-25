"""Bounded-memory graph-based restoration candidate generation.

The ranking proxy is not a physical loss calculation. Final electrical
feasibility and physical real losses must come from OpenDSS.
"""
from dataclasses import dataclass, field
from collections import deque
from itertools import combinations
import heapq
import math


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


def _recovery_path_context(net, faulted_branches):
    """Describe source-disconnected buses, entry ties, and source paths.

    The base active graph contains normally closed branches except faulted
    branches. Its source component defines supplied buses; every other bus is
    part of the outage region. Paths are obtained by traversing that actual
    active graph, without relying on bus numbering or tie identifiers.
    """
    faulted = set(faulted_branches)
    adjacency = {bus: [] for bus in net.buses}

    for branch in net.branches:
        if branch.normally_closed and branch.branch_id not in faulted:
            adjacency[branch.u].append((branch.v, branch))
            adjacency[branch.v].append((branch.u, branch))

    parents = {}
    parent_branches = {}
    source = net.source_bus
    if source in adjacency:
        parents[source] = None
        queue = deque([source])
        while queue:
            bus = queue.popleft()
            for neighbor, branch in adjacency[bus]:
                if neighbor in parents:
                    continue
                parents[neighbor] = bus
                parent_branches[neighbor] = branch.branch_id
                queue.append(neighbor)

    source_buses = set(parents)
    outage_buses = set(net.buses) - source_buses
    boundary_ties = {}
    source_paths = {}

    for branch in net.branches:
        if branch.normally_closed or branch.branch_id in faulted:
            continue
        u_in_source = branch.u in source_buses
        v_in_source = branch.v in source_buses
        u_in_outage = branch.u in outage_buses
        v_in_outage = branch.v in outage_buses
        if not (
            (u_in_source and v_in_outage)
            or (v_in_source and u_in_outage)
        ):
            continue

        source_endpoint = branch.u if u_in_source else branch.v
        path = []
        bus = source_endpoint
        while bus != source:
            path.append(parent_branches[bus])
            bus = parents[bus]
        path.reverse()

        boundary_ties[branch.branch_id] = {
            "outage_bus": branch.v if u_in_source else branch.u,
            "source_bus": source_endpoint,
        }
        source_paths[branch.branch_id] = tuple(path)

    return outage_buses, boundary_ties, source_paths


def _candidate_rank_key(plan, source_paths):
    """Higher keys are better; path relevance follows load and operations."""
    closed_ties = set(plan.close_ties)
    opened_branches = set(plan.open_branches)
    path_relevant = plan.valid and any(
        tie_id in closed_ties
        and not opened_branches.intersection(path_branches)
        for tie_id, path_branches in source_paths.items()
    )
    return (
        plan.restored_kw,
        -plan.switching_operations,
        int(path_relevant),
        -plan.estimated_loss_kw,
    )


def _candidate_state(net, close, opened, faulted):
    """Return (valid, errors, supplied buses, adjacency) without NetworkX.

    A disjoint-set check detects cycles, then a small BFS finds the source-
    connected section. This is substantially cheaper than allocating a
    NetworkX graph for every switching combination.
    """
    errors = []
    close_set, opened_set, faulted_set = set(close), set(opened), set(faulted)
    requested = close_set | opened_set | faulted_set
    unknown = sorted(requested - set(net.branch_by_id))
    if unknown:
        return False, [f"Unknown branch ID: {bid}" for bid in unknown], [], {}

    if close_set & opened_set:
        errors.append("A branch cannot be both opened and closed.")
    if faulted_set & (close_set | opened_set):
        errors.append("A faulted branch cannot also be switched.")

    for bid in close_set:
        branch = net.branch_by_id[bid]
        if branch.normally_closed or not branch.switchable:
            errors.append(f"{bid} is not a switchable normally-open tie.")
    for bid in opened_set:
        branch = net.branch_by_id[bid]
        if not branch.normally_closed or not branch.switchable:
            errors.append(f"{bid} is not a switchable normally-closed branch.")
    if errors:
        return False, errors, [], {}

    parent = {bus: bus for bus in net.buses}
    rank = {bus: 0 for bus in net.buses}

    def find(bus):
        while parent[bus] != bus:
            parent[bus] = parent[parent[bus]]
            bus = parent[bus]
        return bus

    def union(a, b):
        ra, rb = find(a), find(b)
        if ra == rb:
            return False
        if rank[ra] < rank[rb]:
            ra, rb = rb, ra
        parent[rb] = ra
        if rank[ra] == rank[rb]:
            rank[ra] += 1
        return True

    adjacency = {bus: [] for bus in net.buses}
    for branch in net.branches:
        bid = branch.branch_id
        active = bid not in opened_set and bid not in faulted_set and (
            branch.normally_closed or bid in close_set
        )
        if not active:
            continue
        if not union(branch.u, branch.v):
            return False, ["Topology is not radial; a cycle exists."], [], {}
        adjacency[branch.u].append((branch.v, branch))
        adjacency[branch.v].append((branch.u, branch))

    if net.source_bus not in adjacency:
        return False, ["Source bus is missing from the network."], [], {}

    supplied = set()
    stack = [net.source_bus]
    while stack:
        bus = stack.pop()
        if bus in supplied:
            continue
        supplied.add(bus)
        stack.extend(neighbor for neighbor, _ in adjacency[bus] if neighbor not in supplied)

    return True, [], sorted(supplied), adjacency


def _loss_proxy(net, supplied_buses, adjacency):
    """Calculate a simple resistance/downstream-load ranking proxy (not kW losses)."""
    supplied = set(supplied_buses)
    source = net.source_bus
    if source not in supplied:
        return 0.0

    order, parents = [], {}
    stack = [(source, None)]
    seen = set()
    while stack:
        bus, parent = stack.pop()
        if bus in seen:
            continue
        seen.add(bus)
        order.append(bus)
        if parent is not None:
            parents[bus] = parent
        for neighbor, branch in adjacency[bus]:
            if neighbor in supplied and neighbor not in seen:
                stack.append((neighbor, bus))

    subtree_load = {
        bus: float(net.buses[bus].get("load_kw", 0.0)) for bus in order
    }
    for bus in reversed(order):
        parent = parents.get(bus)
        if parent is not None:
            subtree_load[parent] += subtree_load[bus]

    total = 0.0
    for bus, parent in parents.items():
        branch = next(b for neighbor, b in adjacency[parent] if neighbor == bus)
        downstream_mw = subtree_load[bus] / 1000.0
        total += float(branch.resistance_ohm) * downstream_mw**2
    return round(total, 6)


def find_restoration_plans(
    net,
    faulted_branches=None,
    max_operations=3,
    max_results=10,
):
    """Enumerate switching combinations but retain only the best ``max_results``.

    Memory usage is O(max_results), rather than storing every combination.
    Candidate generation still considers the requested operation-depth search;
    use a small max_operations value for practical restoration searches.
    """
    faulted = set(faulted_branches or [])
    if isinstance(max_operations, bool) or not isinstance(max_operations, int) or max_operations < 0:
        raise ValueError("max_operations must be a non-negative integer")
    if isinstance(max_results, bool) or not isinstance(max_results, int):
        raise ValueError("max_results must be a positive integer")
    if max_results < 1:
        return []

    unknown_faults = sorted(faulted - set(net.branch_by_id))
    if unknown_faults:
        raise ValueError(f"Unknown faulted branch IDs: {', '.join(unknown_faults)}")

    _, _, source_paths = _recovery_path_context(net, faulted)

    ties = [b.branch_id for b in net.branches
            if not b.normally_closed and b.switchable and b.branch_id not in faulted]
    lines = [b.branch_id for b in net.branches
             if b.normally_closed and b.switchable and b.branch_id not in faulted]
    total_load = net.total_load_kw()
    heap = []
    serial = 0

    for nclose in range(min(len(ties), max_operations) + 1):
        for close in combinations(ties, nclose):
            remaining = max_operations - nclose
            for nopen in range(min(len(lines), remaining) + 1):
                for opened in combinations(lines, nopen):
                    valid, errors, supplied, adjacency = _candidate_state(
                        net, close, opened, faulted
                    )
                    restored = sum(
                        float(net.buses[bus].get("load_kw", 0.0)) for bus in supplied
                    )
                    pct = 100.0 * restored / total_load if total_load else 100.0
                    operations = nclose + nopen

                    if valid:
                        # Loss proxy only affects ordering after restored load and
                        # switching count; calculate it only for graph-valid plans.
                        proxy = _loss_proxy(net, supplied, adjacency)
                    else:
                        proxy = math.inf

                    score = pct - operations * 1.5 - (proxy * 0.01 if math.isfinite(proxy) else 1e9)
                    plan = RestorationPlan(
                        close_ties=list(close), open_branches=list(opened),
                        restored_kw=round(restored, 3), restoration_pct=round(pct, 2),
                        switching_operations=operations, supplied_buses=supplied,
                        valid=valid, errors=errors, estimated_loss_kw=proxy,
                        score=round(score, 4),
                    )
                    # Path relevance breaks ties only after restored load and
                    # switching count, and before the existing loss proxy.
                    rank_key = _candidate_rank_key(plan, source_paths)
                    item = (rank_key, serial, plan)
                    serial += 1
                    if len(heap) < max_results:
                        heapq.heappush(heap, item)
                    elif rank_key > heap[0][0]:
                        heapq.heapreplace(heap, item)

    plans = [item[2] for item in heap]
    plans.sort(
        key=lambda p: (
            not p.valid,
            -p.restored_kw,
            p.switching_operations,
            -_candidate_rank_key(p, source_paths)[2],
            p.estimated_loss_kw,
        )
    )
    return plans
