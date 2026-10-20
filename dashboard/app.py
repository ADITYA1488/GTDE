import streamlit as st
import pandas as pd
import networkx as nx
import plotly.graph_objects as go

from src.demo_network import build_demo_network
from src.restoration import find_restoration_plans
from src.powerflow import evaluate_power_flow


st.set_page_config(
    page_title="GraD Feeder Restoration",
    page_icon="⚡",
    layout="wide",
)

st.title("⚡ GraD — Feeder Restoration Engine")
st.warning(
    "Demonstration using synthetic feeder data. "
    "Not intended for real grid switching."
)

net = build_demo_network()

with st.sidebar:
    st.header("Fault scenario")
    fault = st.selectbox(
        "Faulted branch",
        ["L12", "L23", "L34", "L45", "L56"],
        index=3,
    )
    max_ops = st.slider("Maximum switching operations", 1, 4, 3)
    top_n = st.slider("Plans to return", 1, 10, 5)
    run = st.button("Search restoration plans")

faulted = {fault}
graph = net.build_graph(faulted_branches=faulted)
total = net.total_load_kw()
restored = net.restored_load_kw(graph)

a, b, c = st.columns(3)
a.metric("Total load", f"{total:.0f} kW")
b.metric("Initially supplied", f"{restored:.0f} kW")
c.metric("Disconnected", f"{total - restored:.0f} kW")


def draw_graph(g, title):
    pos = nx.spring_layout(g, seed=7)
    fig = go.Figure()

    for u, v, data in g.edges(data=True):
        fig.add_trace(go.Scatter(
            x=[pos[u][0], pos[v][0]],
            y=[pos[u][1], pos[v][1]],
            mode="lines",
            line=dict(width=2),
            text=[data.get("branch_id", ""), data.get("branch_id", "")],
            hoverinfo="text",
            showlegend=False,
        ))

    supplied_buses = net.supplied_buses(g)
    nodes = list(g.nodes())

    fig.add_trace(go.Scatter(
        x=[pos[n][0] for n in nodes],
        y=[pos[n][1] for n in nodes],
        mode="markers+text",
        text=[f"Bus {n}" for n in nodes],
        textposition="top center",
        marker=dict(size=20),
        hovertext=[
            f"Bus {n}: {net.buses[n].get('load_kw', 0)} kW; "
            f"{'supplied' if n in supplied_buses else 'disconnected'}"
            for n in nodes
        ],
        hoverinfo="text",
        showlegend=False,
    ))

    fig.update_layout(
        title=title,
        height=400,
        xaxis=dict(visible=False),
        yaxis=dict(visible=False),
    )
    return fig


st.plotly_chart(draw_graph(graph, f"Topology after fault {fault}"),
                use_container_width=True)

if run:
    plans = find_restoration_plans(
        net, faulted_branches=faulted,
        max_operations=max_ops, max_results=top_n,
    )

    rows = []
    for p in plans:
        rows.append({
            "Close ties": ", ".join(p.close_ties) or "—",
            "Open branches": ", ".join(p.open_branches) or "—",
            "Restored kW": p.restored_kw,
            "Restoration %": p.restoration_pct,
            "Operations": p.switching_operations,
            "Topology valid": p.valid,
            "Graph proxy (not kW)": p.estimated_loss_kw,
        })

    st.subheader("Candidate plans")
    st.dataframe(pd.DataFrame(rows), use_container_width=True)

    if plans:
        best = plans[0]
        st.subheader("Electrical evaluation of first ranked plan")
        result = evaluate_power_flow(
            net,
            set(best.close_ties),
            set(best.open_branches),
            faulted,
        )
        st.json(result)