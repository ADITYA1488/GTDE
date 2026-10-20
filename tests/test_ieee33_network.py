
import networkx as nx

from src.ieee33_network import build_ieee33_network


def test_ieee33_network_dimensions():
    net = build_ieee33_network()

    assert len(net.buses) == 33
    assert len(net.branches) == 37
    assert net.total_load_kw() == 3715.0


def test_ieee33_initial_topology():
    net = build_ieee33_network()
    graph = net.build_graph()

    assert nx.is_tree(graph)
    assert len(net.supplied_buses(graph)) == 33


def test_ieee33_branch_configuration():
    net = build_ieee33_network()

    closed = [b for b in net.branches if b.normally_closed]
    ties = [b for b in net.branches if not b.normally_closed]

    assert len(closed) == 32
    assert len(ties) == 5
    assert all(b.switchable for b in net.branches)
