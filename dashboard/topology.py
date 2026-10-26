"""Model-driven topology data and Plotly view for the Streamlit demo."""

from __future__ import annotations

import networkx as nx
import plotly.graph_objects as go


VIEWS = ("Pre-fault", "Post-fault", "Candidate restoration")
BENCHMARK_FAULTS = ("L05", "L10", "L15", "L20", "L25", "L30")


def supported_faults(net):
    """Return the benchmark fault scenarios available in this network."""
    main_branches = {b.branch_id for b in net.branches if b.normally_closed}
    available = [fault for fault in BENCHMARK_FAULTS if fault in main_branches]
    return available or sorted(main_branches)


def bus_positions(net):
    """Return a readable fixed 2D layout for IEEE-33 buses.

    Coordinates are visual only. All lines and their endpoints are read from
    ``net.branches``; no electrical result or topology is inferred from the
    coordinates.
    """
    ids = sorted(net.buses)
    positions = {}
    if set(ids) == set(range(1, 34)):
        positions.update({bus: (bus - 1, 3.0) for bus in range(1, 19)})
        positions.update({bus: (bus - 18, 2.0) for bus in range(19, 23)})
        positions.update({bus: (bus - 22, 1.0) for bus in range(23, 26)})
        positions.update({bus: (bus - 25, 0.0) for bus in range(26, 34)})
        return positions

    # For other networks, use their actual graph to create a deterministic
    # layered layout. It is still only a schematic, not a geographic layout.
    graph = net.build_graph()
    if net.source_bus in graph:
        depths = nx.single_source_shortest_path_length(graph, net.source_bus)
    else:
        depths = {}
    by_depth = {}
    for bus in ids:
        by_depth.setdefault(depths.get(bus, max(depths.values(), default=0) + 1), []).append(bus)
    for depth, buses in by_depth.items():
        for position, bus in enumerate(sorted(buses)):
            positions[bus] = (depth, -position)
    return positions


def topology_state(net, faulted_branches=(), plan=None, view="Post-fault"):
    """Build actual active graph, bus sets, branch states, and recovery path."""
    if view not in VIEWS:
        raise ValueError(f"view must be one of {VIEWS!r}")
    faults = set(faulted_branches or ()) if view != "Pre-fault" else set()
    close_ties = set(getattr(plan, "close_ties", ())) if view == "Candidate restoration" else set()
    open_branches = set(getattr(plan, "open_branches", ())) if view == "Candidate restoration" else set()
    graph = net.build_graph(
        closed_ties=close_ties,
        opened_branches=open_branches,
        faulted_branches=faults,
    )
    supplied = net.supplied_buses(graph)
    disconnected = set(net.buses) - supplied

    post_fault_graph = net.build_graph(faulted_branches=faults)
    post_fault_supplied = net.supplied_buses(post_fault_graph)
    recovered = supplied - post_fault_supplied if view == "Candidate restoration" else set()

    path_branch_ids = set()
    if recovered and net.source_bus in graph:
        for bus in recovered:
            try:
                path = nx.shortest_path(graph, net.source_bus, bus)
            except (nx.NetworkXNoPath, nx.NodeNotFound):
                continue
            path_branch_ids.update(
                graph[u][v].get("branch_id") for u, v in zip(path, path[1:])
            )
    path_branch_ids.discard(None)

    branches = []
    for branch in net.branches:
        bid = branch.branch_id
        if bid in faults:
            state = "faulted"
        elif bid in open_branches:
            state = "opened by candidate"
        elif bid in close_ties:
            state = "closed by candidate"
        elif graph.has_edge(branch.u, branch.v):
            state = (
                "energized"
                if branch.u in supplied and branch.v in supplied
                else "de-energized segment"
            )
        elif not branch.normally_closed:
            state = "normally open tie"
        else:
            state = "open"
        branches.append({
            "branch_id": bid,
            "u": branch.u,
            "v": branch.v,
            "state": state,
            "path": bid in path_branch_ids,
            "active": graph.has_edge(branch.u, branch.v),
        })

    return {
        "graph": graph,
        "supplied_buses": supplied,
        "disconnected_buses": disconnected,
        "recovered_buses": recovered,
        "branches": branches,
        "recovery_path_branches": path_branch_ids,
    }


def build_feeder_figure(net, faulted_branches=(), plan=None, view="Post-fault", selected_bus=None):
    """Draw the feeder from model branch endpoints and actual switch state."""
    state = topology_state(net, faulted_branches, plan, view)
    positions = bus_positions(net)
    fig = go.Figure()
    colors = {
        "energized": ("#64748b", "solid", 2.0),
        "de-energized segment": ("#94a3b8", "solid", 2.0),
        "faulted": ("#dc2626", "dash", 4.0),
        "normally open tie": ("#2563eb", "dash", 2.0),
        "opened by candidate": ("#d97706", "dash", 3.5),
        "closed by candidate": ("#16a34a", "solid", 3.5),
        "open": ("#cbd5e1", "dot", 1.4),
    }
    for branch in state["branches"]:
        u, v = branch["u"], branch["v"]
        x1, y1 = positions[u]
        x2, y2 = positions[v]
        color, dash, width = colors[branch["state"]]
        if branch["path"]:
            color, dash, width = "#9333ea", "solid", 5.0
        legend_name = "Selected recovery path" if branch["path"] else branch["state"]
        fig.add_trace(go.Scatter(
            x=[x1, x2], y=[y1, y2], mode="lines",
            line={"color": color, "dash": dash, "width": width},
            name=legend_name, legendgroup=legend_name,
            showlegend=not any(t.name == legend_name for t in fig.data),
            customdata=[[branch["branch_id"], u, v, branch["state"]]] * 2,
            hovertemplate="%{customdata[0]} · Bus %{customdata[1]}—%{customdata[2]} · %{customdata[3]}<extra></extra>",
        ))

    bus_ids = sorted(net.buses)
    bus_colors = [
        "#dc2626" if bus == net.source_bus else
        "#9333ea" if bus in state["recovered_buses"] else
        "#94a3b8" if bus in state["disconnected_buses"] else
        "#0f766e"
        for bus in bus_ids
    ]
    if selected_bus in net.buses:
        bus_colors[bus_ids.index(selected_bus)] = "#f59e0b"
    custom = [[
        bus, net.buses[bus].get("name", f"Bus {bus}"),
        float(net.buses[bus].get("load_kw", 0)),
        net.buses[bus].get("load_priority_weight", 1.0),
        "source" if bus == net.source_bus else
        "disconnected" if bus in state["disconnected_buses"] else
        "recovered" if bus in state["recovered_buses"] else "energized",
    ] for bus in bus_ids]
    fig.add_trace(go.Scatter(
        x=[positions[bus][0] for bus in bus_ids],
        y=[positions[bus][1] for bus in bus_ids],
        mode="markers+text", text=[str(bus) for bus in bus_ids],
        textposition="top center", textfont={"size": 10, "color": "#1f2937"},
        marker={"size": 12, "color": bus_colors, "line": {"width": 1, "color": "white"}},
        customdata=custom,
        hovertemplate="%{customdata[1]} (%{customdata[4]})<br>Bus %{customdata[0]}<br>Load: %{customdata[2]:.1f} kW<extra></extra>",
        name="Buses", showlegend=False,
    ))
    fig.update_layout(
        height=520, margin={"l": 20, "r": 20, "t": 20, "b": 20},
        plot_bgcolor="white", paper_bgcolor="white", hovermode="closest",
        font={"color": "#1f2937"},
        legend={"orientation": "h", "y": -0.08, "font": {"color": "#1f2937"}},
        xaxis={"visible": False}, yaxis={"visible": False, "scaleanchor": "x", "scaleratio": 1},
    )
    return fig


def candidate_label(index, result):
    """Stable user-facing candidate selector label."""
    return (
        f"Candidate {index + 1} · close {','.join(result.plan.close_ties) or 'none'}"
        f" · open {','.join(result.plan.open_branches) or 'none'}"
    )


def select_candidate(results, index):
    """Select an evaluated candidate by its displayed zero-based index."""
    if not results:
        return None
    if not isinstance(index, int) or index < 0 or index >= len(results):
        raise IndexError("candidate index is outside the evaluated result list")
    return results[index]
