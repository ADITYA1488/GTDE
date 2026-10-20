from dataclasses import dataclass
import networkx as nx


@dataclass(frozen=True)
class Branch:
    branch_id: str
    u: int
    v: int
    normally_closed: bool
    switchable: bool = True
    resistance_ohm: float = 0.2


class DistributionNetwork:
    def __init__(self, buses, branches, source_bus=1):
        self.buses = buses
        self.branches = branches
        self.source_bus = source_bus
        self.branch_by_id = {
            branch.branch_id: branch for branch in branches
        }

    def build_graph(
        self, closed_ties=None, opened_branches=None,
        faulted_branches=None
    ):
        closed_ties = set(closed_ties or [])
        opened_branches = set(opened_branches or [])
        faulted_branches = set(faulted_branches or [])

        graph = nx.Graph()
        graph.add_nodes_from(self.buses)

        for branch in self.branches:
            bid = branch.branch_id

            if bid in opened_branches or bid in faulted_branches:
                continue

            if branch.normally_closed or bid in closed_ties:
                graph.add_edge(
                    branch.u, branch.v,
                    branch_id=bid,
                    resistance_ohm=branch.resistance_ohm
                )

        return graph

    def supplied_buses(self, graph):
        if self.source_bus not in graph:
            return set()
        return set(nx.node_connected_component(graph, self.source_bus))

    def total_load_kw(self):
        return sum(
            float(bus.get("load_kw", 0))
            for bus in self.buses.values()
        )

    def restored_load_kw(self, graph):
        supplied = self.supplied_buses(graph)
        return sum(
            float(bus.get("load_kw", 0))
            for bus_id, bus in self.buses.items()
            if bus_id in supplied
        )

    def validate_topology(
        self, closed_ties=None, opened_branches=None,
        faulted_branches=None
    ):
        closed_ties = set(closed_ties or [])
        opened_branches = set(opened_branches or [])
        faulted_branches = set(faulted_branches or [])

        errors = []
        requested = closed_ties | opened_branches | faulted_branches

        for bid in requested:
            if bid not in self.branch_by_id:
                errors.append(f"Unknown branch ID: {bid}")

        for bid in closed_ties:
            branch = self.branch_by_id.get(bid)
            if branch and branch.normally_closed:
                errors.append(f"{bid} is not a normally-open tie.")

        for bid in opened_branches:
            branch = self.branch_by_id.get(bid)
            if branch and not branch.normally_closed:
                errors.append(f"{bid} is not a normally-closed branch.")
            if branch and not branch.switchable:
                errors.append(f"{bid} is not switchable.")

        if errors:
            return errors

        graph = self.build_graph(
            closed_ties, opened_branches, faulted_branches
        )

        if not nx.is_forest(graph):
            errors.append("Topology is not radial; a cycle exists.")

        return errors