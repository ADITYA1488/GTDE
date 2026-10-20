from pathlib import Path

import networkx as nx
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from src.ieee33_network import build_ieee33_network


ROOT = Path(__file__).resolve().parents[1]
RESULTS_FILE = ROOT / "results" / "combined_optimization_benchmark.csv"

VOLTAGE_MIN_PU = 0.95
VOLTAGE_MAX_PU = 1.05


st.set_page_config(
    page_title="GTDE | Grid Optimization",
    page_icon="⚡",
    layout="wide",
)

st.title("⚡ GTDE — Grid Topology and Distribution Optimization")
st.caption(
    "IEEE 33-bus network | OpenDSS power flow | "
    "Radial reconfiguration and capacitor-support benchmark"
)

st.info(
    "This dashboard displays saved simulation results. "
    "It does not operate or switch a real electrical grid."
)


# ---------------------------------------------------------
# Load benchmark results
# ---------------------------------------------------------

if not RESULTS_FILE.exists():
    st.error(
        "Combined benchmark results were not found. "
        "Run benchmark_combined_optimization.py first."
    )
    st.stop()

df = pd.read_csv(RESULTS_FILE)

required_columns = {
    "scenario",
    "configuration",
    "feasible",
    "min_voltage_pu",
    "max_voltage_pu",
    "real_losses_kw",
    "load_served_pct",
    "capacitor_bus",
    "capacitor_kvar",
}

missing = required_columns - set(df.columns)

if missing:
    st.error(f"Benchmark CSV is missing columns: {sorted(missing)}")
    st.stop()

# CSV booleans are normally parsed as bool, but normalize defensively.
df["feasible"] = (
    df["feasible"]
    .astype(str)
    .str.strip()
    .str.lower()
    .eq("true")
)

df["real_losses_kw"] = pd.to_numeric(
    df["real_losses_kw"], errors="coerce"
)
df["min_voltage_pu"] = pd.to_numeric(
    df["min_voltage_pu"], errors="coerce"
)
df["max_voltage_pu"] = pd.to_numeric(
    df["max_voltage_pu"], errors="coerce"
)
df["load_served_pct"] = pd.to_numeric(
    df["load_served_pct"], errors="coerce"
)

df["capacitor_kvar"] = pd.to_numeric(
    df["capacitor_kvar"], errors="coerce"
).fillna(0)

df["capacitor_bus"] = pd.to_numeric(
    df["capacitor_bus"], errors="coerce"
)

base_matches = df[
    (df["configuration"] == "base")
    & (df["capacitor_kvar"] == 0)
]

if base_matches.empty:
    st.error("No base-case result was found in the benchmark CSV.")
    st.stop()

base = base_matches.iloc[0]

feasible_df = df[
    df["feasible"]
    & df["real_losses_kw"].notna()
    & df["min_voltage_pu"].notna()
    & df["max_voltage_pu"].notna()
].copy()

feasible_df = feasible_df.sort_values("real_losses_kw")

if feasible_df.empty:
    st.warning(
        "No feasible configuration is present in the saved results. "
        "Review the constraint violations before selecting a candidate."
    )
    st.stop()


# ---------------------------------------------------------
# Sidebar
# ---------------------------------------------------------

st.sidebar.header("Optimization results")

st.sidebar.metric("Scenarios evaluated", f"{len(df):,}")
st.sidebar.metric("Feasible scenarios", f"{len(feasible_df):,}")

selected_scenario = st.sidebar.selectbox(
    "Select a feasible configuration",
    feasible_df["scenario"].tolist(),
    index=0,
)

selected = feasible_df[
    feasible_df["scenario"] == selected_scenario
].iloc[0]


# ---------------------------------------------------------
# Main metrics
# ---------------------------------------------------------

base_losses = float(base["real_losses_kw"])
best_losses = float(selected["real_losses_kw"])

loss_reduction_kw = base_losses - best_losses

loss_reduction_pct = (
    100 * loss_reduction_kw / base_losses
    if base_losses > 0
    else 0.0
)

col1, col2, col3, col4 = st.columns(4)

col1.metric(
    "Base real losses",
    f"{base_losses:.3f} kW",
)

col2.metric(
    "Selected real losses",
    f"{best_losses:.3f} kW",
    delta=f"{-loss_reduction_kw:.3f} kW",
    delta_color="inverse",
)

col3.metric(
    "Loss reduction",
    f"{loss_reduction_pct:.2f}%",
)

col4.metric(
    "Minimum voltage",
    f"{selected['min_voltage_pu']:.6f} pu",
)

st.divider()


# ---------------------------------------------------------
# Selected configuration
# ---------------------------------------------------------

st.subheader("Selected optimization configuration")

left, right = st.columns(2)

with left:
    st.markdown("**Switching actions**")

    close_ties = str(selected.get("close_ties", "") or "").strip()
    open_lines = str(selected.get("open_branches", "") or "").strip()

    st.write(
        f"Close tie: {close_ties if close_ties else 'None'}"
    )
    st.write(
        f"Open branch: {open_lines if open_lines else 'None'}"
    )

with right:
    st.markdown("**Capacitor support**")

    cap_bus = selected["capacitor_bus"]
    cap_kvar = float(selected["capacitor_kvar"])

    if pd.isna(cap_bus) or cap_kvar <= 0:
        st.write("No capacitor bank selected.")
    else:
        st.write(f"Bus: {int(cap_bus)}")
        st.write(f"Rated reactive power: {cap_kvar:.0f} kVAr")

    st.write(
        f"Maximum voltage: {selected['max_voltage_pu']:.6f} pu"
    )
    st.write(
        f"Load served: {selected['load_served_pct']:.3f}%"
    )

st.success(
    "Selected configuration is marked feasible in the saved benchmark."
)


# ---------------------------------------------------------
# Voltage and losses comparison
# ---------------------------------------------------------

st.subheader("Base case versus selected configuration")

comparison = pd.DataFrame(
    {
        "Metric": [
            "Minimum voltage (pu)",
            "Maximum voltage (pu)",
            "Real losses (kW)",
        ],
        "Base case": [
            base["min_voltage_pu"],
            base["max_voltage_pu"],
            base["real_losses_kw"],
        ],
        "Selected configuration": [
            selected["min_voltage_pu"],
            selected["max_voltage_pu"],
            selected["real_losses_kw"],
        ],
    }
)

st.dataframe(
    comparison,
    hide_index=True,
    use_container_width=True,
)

voltage_fig = go.Figure()

voltage_fig.add_trace(
    go.Bar(
        name="Base case",
        x=["Minimum voltage", "Maximum voltage"],
        y=[
            base["min_voltage_pu"],
            base["max_voltage_pu"],
        ],
    )
)

voltage_fig.add_trace(
    go.Bar(
        name="Selected configuration",
        x=["Minimum voltage", "Maximum voltage"],
        y=[
            selected["min_voltage_pu"],
            selected["max_voltage_pu"],
        ],
    )
)

voltage_fig.add_hline(
    y=VOLTAGE_MIN_PU,
    line_dash="dash",
    annotation_text="Minimum voltage limit",
)

voltage_fig.add_hline(
    y=VOLTAGE_MAX_PU,
    line_dash="dash",
    annotation_text="Maximum voltage limit",
)

voltage_fig.update_layout(
    title="Voltage extrema comparison",
    yaxis_title="Voltage (pu)",
    barmode="group",
    height=400,
)

st.plotly_chart(voltage_fig, use_container_width=True)


# ---------------------------------------------------------
# Network topology
# ---------------------------------------------------------

st.subheader("Network topology")

try:
    net = build_ieee33_network()

    close_ties = [
        item.strip()
        for item in str(selected.get("close_ties", "") or "").split(";")
        if item.strip()
    ]

    open_branches = [
        item.strip()
        for item in str(selected.get("open_branches", "") or "").split(";")
        if item.strip()
    ]

    graph = net.build_graph(
        closed_ties=close_ties,
        opened_branches=open_branches,
    )

    positions = nx.spring_layout(graph, seed=7)

    edge_x = []
    edge_y = []

    for u, v in graph.edges():
        edge_x.extend([
            positions[u][0],
            positions[v][0],
            None,
        ])
        edge_y.extend([
            positions[u][1],
            positions[v][1],
            None,
        ])

    topology_fig = go.Figure()

    topology_fig.add_trace(
        go.Scatter(
            x=edge_x,
            y=edge_y,
            mode="lines",
            line=dict(width=1.5, color="gray"),
            hoverinfo="skip",
            showlegend=False,
        )
    )

    supplied = net.supplied_buses(graph)
    nodes = list(graph.nodes())

    topology_fig.add_trace(
        go.Scatter(
            x=[positions[n][0] for n in nodes],
            y=[positions[n][1] for n in nodes],
            mode="markers+text",
            text=[str(n) for n in nodes],
            textposition="top center",
            marker=dict(
                size=12,
                color=[
                    "#16a34a" if n in supplied else "#dc2626"
                    for n in nodes
                ],
            ),
            hovertext=[
                f"Bus {n}<br>"
                f"{'Supplied' if n in supplied else 'Not supplied'}"
                for n in nodes
            ],
            hoverinfo="text",
            showlegend=False,
        )
    )

    topology_fig.update_layout(
        title="Selected network topology (bus labels)",
        height=550,
        xaxis=dict(visible=False),
        yaxis=dict(visible=False),
    )

    st.plotly_chart(topology_fig, use_container_width=True)

    st.caption(
        "Green buses are connected to the source in the network graph. "
        "This graph shows topology, not the electrical voltage profile."
    )

except Exception as exc:
    st.warning(f"Could not render the network topology: {exc}")


# ---------------------------------------------------------
# Candidate comparison
# ---------------------------------------------------------

st.subheader("Feasible candidate comparison")

display_columns = [
    "scenario",
    "close_ties",
    "open_branches",
    "capacitor_bus",
    "capacitor_kvar",
    "min_voltage_pu",
    "max_voltage_pu",
    "real_losses_kw",
    "load_served_pct",
]

display_columns = [
    col for col in display_columns
    if col in feasible_df.columns
]

st.dataframe(
    feasible_df[display_columns].reset_index(drop=True),
    hide_index=True,
    use_container_width=True,
)

loss_fig = go.Figure()

loss_fig.add_trace(
    go.Bar(
        x=feasible_df["scenario"],
        y=feasible_df["real_losses_kw"],
        name="Real losses",
    )
)

loss_fig.update_layout(
    title="Real losses across feasible configurations",
    xaxis_title="Configuration",
    yaxis_title="Real losses (kW)",
    height=450,
)

st.plotly_chart(loss_fig, use_container_width=True)


# ---------------------------------------------------------
# Download results
# ---------------------------------------------------------

st.subheader("Export")

st.download_button(
    "Download complete benchmark CSV",
    data=df.to_csv(index=False).encode("utf-8"),
    file_name="combined_optimization_benchmark.csv",
    mime="text/csv",
)

st.caption(
    "GTDE is a research/demo application. "
    "Validate electrical models and operating constraints before "
    "using any result for real-world grid decisions."
)