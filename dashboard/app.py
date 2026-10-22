"""GTDE: Graph-Theory Driven Feeder Reconfiguration and Restoration."""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go

from src.strategy_comparison import compare_strategies
from src.ieee33_network import build_ieee33_network
from src.restoration_powerflow import evaluate_restoration_plans


st.set_page_config(
    page_title="GTDE | Feeder Restoration",
    page_icon="⚡",
    layout="wide",
)

st.title("⚡ GTDE — Feeder Restoration Engine")
st.caption(
    "IEEE 33-bus | Graph-based FLISR | OpenDSS electrical validation"
)


@st.cache_resource
def load_network():
    return build_ieee33_network()


def get_value(obj, *names, default=None):
    """Read a value from an object or dictionary."""
    for name in names:
        if isinstance(obj, dict) and name in obj:
            return obj[name]
        if hasattr(obj, name):
            return getattr(obj, name)
    return default


def draw_network(net, result=None, fault=None):
    """Draw a schematic of the IEEE 33-bus feeder."""

    fig = go.Figure()

    endpoints = {}

    for i in range(1, 18):
        endpoints[f"L{i:02d}"] = (i, i + 1)

    for i, (u, v) in enumerate(
        [(2, 19), (19, 20), (20, 21), (21, 22)],
        start=18,
    ):
        endpoints[f"L{i:02d}"] = (u, v)

    for i, (u, v) in enumerate(
        [(3, 23), (23, 24), (24, 25)],
        start=22,
    ):
        endpoints[f"L{i:02d}"] = (u, v)

    for i, (u, v) in enumerate(
        [
            (6, 26),
            (26, 27),
            (27, 28),
            (28, 29),
            (29, 30),
            (30, 31),
            (31, 32),
            (32, 33),
        ],
        start=25,
    ):
        endpoints[f"L{i:02d}"] = (u, v)

    endpoints.update(
        {
            "T33": (8, 21),
            "T34": (9, 15),
            "T35": (12, 22),
            "T36": (18, 33),
            "T37": (25, 29),
        }
    )

    positions = {}

    for bus in range(1, 19):
        positions[bus] = (bus - 1, 3)

    for bus in range(19, 23):
        positions[bus] = (bus - 18, 2)

    for bus in range(23, 26):
        positions[bus] = (bus - 22, 1)

    for bus in range(26, 34):
        positions[bus] = (bus - 25, 0)

    for branch in getattr(net, "branches", []):
        branch_id = str(
            get_value(branch, "branch_id", "id", default="?")
        )

        u = get_value(
            branch,
            "from_bus",
            "source_bus",
            "u",
            "bus1",
            "from_node",
        )
        v = get_value(
            branch,
            "to_bus",
            "target_bus",
            "v",
            "bus2",
            "to_node",
        )

        try:
            u, v = int(u), int(v)
        except (TypeError, ValueError):
            u, v = endpoints.get(branch_id, (None, None))

        if u not in positions or v not in positions:
            u, v = endpoints.get(branch_id, (None, None))

        if u not in positions or v not in positions:
            continue

        normally_closed = get_value(
            branch, "normally_closed", default=True
        )

        color = "#64748b" if normally_closed else "#2563eb"
        width = 2 if normally_closed else 1.8
        dash = "solid" if normally_closed else "dash"

        if branch_id == str(fault):
            color, width, dash = "#dc2626", 4, "solid"
        elif result is not None:
            if branch_id in result.plan.close_ties:
                color, width, dash = "#16a34a", 3.5, "solid"
            elif branch_id in result.plan.open_branches:
                color, width, dash = "#d97706", 3.5, "dash"

        x1, y1 = positions[u]
        x2, y2 = positions[v]

        fig.add_trace(
            go.Scatter(
                x=[x1, x2],
                y=[y1, y2],
                mode="lines",
                line=dict(color=color, width=width, dash=dash),
                hovertemplate=(
                    f"{branch_id}: Bus {u} — Bus {v}<extra></extra>"
                ),
                showlegend=False,
            )
        )

    bus_ids = sorted(positions)

    fig.add_trace(
        go.Scatter(
            x=[positions[bus][0] for bus in bus_ids],
            y=[positions[bus][1] for bus in bus_ids],
            mode="markers+text",
            text=[str(bus) for bus in bus_ids],
            textposition="top center",
            textfont=dict(size=10, color="#1f2937"),
            marker=dict(
                size=10,
                color=[
                    "#dc2626" if bus == 1 else "#0f766e"
                    for bus in bus_ids
                ],
                line=dict(width=1, color="white"),
            ),
            hovertemplate="Bus %{text}<extra></extra>",
            showlegend=False,
        )
    )

    fig.update_layout(
        height=470,
        margin=dict(l=20, r=20, t=20, b=20),
        plot_bgcolor="white",
        paper_bgcolor="white",
        showlegend=False,
        xaxis=dict(visible=False),
        yaxis=dict(
            visible=False,
            scaleanchor="x",
            scaleratio=1,
        ),
    )

    return fig


# ---------------------------------------------------------
# Network and simulation controls
# ---------------------------------------------------------

net = load_network()

with st.sidebar:
    st.header("Simulation settings")

    branch_ids = [
        branch.branch_id
        for branch in net.branches
        if branch.normally_closed
    ]

    fault = st.selectbox(
        "Faulted main branch",
        branch_ids,
        index=branch_ids.index("L10") if "L10" in branch_ids else 0,
    )

    strategy = st.selectbox(
        "Search strategy",
        ["baseline", "adaptive"],
        index=1,
    )

    max_operations = st.slider(
        "Maximum switching operations",
        min_value=0,
        max_value=5,
        value=3,
    )

    evaluation_budget = st.slider(
        "OpenDSS evaluation budget",
        min_value=1,
        max_value=30,
        value=10,
    )

    capacitor_enabled = st.checkbox(
        "Enable capacitor support",
        value=True,
    )

    capacitor_bus = 33 if capacitor_enabled else None
    capacitor_kvar = 900 if capacitor_enabled else 0

    run = st.button(
        "Run restoration",
        type="primary",
        width="stretch",
    )


# ---------------------------------------------------------
# Run restoration with visible progress
# ---------------------------------------------------------

if run:
    st.session_state.pop("gtde_results", None)
    st.session_state.pop("gtde_fault", None)

    progress = st.progress(0)
    status = st.empty()

    def report_progress(completed, total, result):
        if total <= 0:
            status.write("No graph-valid candidates to evaluate.")
            return

        progress.progress(min(completed / total, 1.0))

        if result is None:
            status.write("Preparing restoration candidates...")
            return

        status.write(
            f"OpenDSS evaluations: {completed}/{total} · "
            f"Converged: {result.converged}"
        )

    try:
        results = evaluate_restoration_plans(
            net,
            faulted_branches={fault},
            max_operations=max_operations,
            max_results=10,
            capacitor_bus=capacitor_bus,
            capacitor_kvar=capacitor_kvar,
            max_electrical_evaluations=evaluation_budget,
            strategy=strategy,
            progress_callback=report_progress,
        )

        st.session_state["gtde_results"] = results
        st.session_state["gtde_fault"] = fault
        st.session_state["gtde_strategy"] = strategy

        progress.progress(1.0)
        status.success(
            f"Evaluation finished. {len(results)} result(s) returned."
        )

    except Exception as exc:
        status.error("Restoration evaluation failed.")
        st.exception(exc)


# ---------------------------------------------------------
# Results
# ---------------------------------------------------------

results = st.session_state.get("gtde_results", [])
active_fault = st.session_state.get("gtde_fault", fault)

if not results:
    st.info("Choose simulation settings and click Run restoration.")
    st.plotly_chart(
        draw_network(net, fault=active_fault),
        width="stretch",
    )
    st.stop()


feasible = [
    result
    for result in results
    if (
        result.converged
        and result.voltage_feasible
        and result.graph_electrical_consistent
    )
]

best = feasible[0] if feasible else None

st.subheader("Restoration overview")

c1, c2, c3, c4 = st.columns(4)

c1.metric(
    "Feasible candidates",
    f"{len(feasible)} / {len(results)}",
)

c2.metric(
    "Restored load",
    f"{best.plan.restored_kw:,.1f} kW" if best else "None",
)

c3.metric(
    "Minimum voltage",
    (
        f"{best.min_voltage_pu:.4f} pu"
        if best and best.min_voltage_pu is not None
        else "—"
    ),
)

c4.metric(
    "Real losses",
    (
        f"{best.real_losses_kw:.3f} kW"
        if best and best.real_losses_kw is not None
        else "—"
    ),
)

if best:
    st.success(
        f"Best feasible candidate: close "
        f"{best.plan.close_ties or 'none'}; open "
        f"{best.plan.open_branches or 'none'}."
    )
else:
    st.warning(
        "No candidate passed all current electrical feasibility checks. "
        "Review the diagnostics before selecting a plan."
    )


# ---------------------------------------------------------
# Electrical diagnostics
# ---------------------------------------------------------

with st.expander(
    "Electrical feasibility diagnostics",
    expanded=not bool(feasible),
):
    diagnostic_rows = []

    for index, result in enumerate(results, start=1):
        diagnostic_rows.append(
            {
                "Candidate": index,
                "Close ties": ", ".join(result.plan.close_ties) or "—",
                "Open branches": (
                    ", ".join(result.plan.open_branches) or "—"
                ),
                "Converged": result.converged,
                "Voltage feasible": result.voltage_feasible,
                "Graph consistent": result.graph_electrical_consistent,
                "Minimum voltage (pu)": result.min_voltage_pu,
                "Maximum voltage (pu)": result.max_voltage_pu,
                "Losses (kW)": result.real_losses_kw,
                "Thermal status": result.thermal_status,
                "Rejection reason": (
                    result.rejection_reason or "No rejection reason"
                ),
            }
        )

    st.dataframe(
        pd.DataFrame(diagnostic_rows),
        width="stretch",
        hide_index=True,
    )

    st.caption(
        "A candidate must converge, satisfy voltage limits, and pass "
        "the graph/electrical consistency check. Thermal safety remains "
        "unassessed without verified ampacity ratings."
    )


# ---------------------------------------------------------
# Topology and switching decision
# ---------------------------------------------------------

left, right = st.columns([1.4, 1])

with left:
    st.subheader("Feeder topology")

    st.plotly_chart(
        draw_network(net, result=best, fault=active_fault),
        width="stretch",
    )

    st.caption(
        "Schematic only. Green = selected tie closures; orange = "
        "selected openings; red = faulted branch; blue dashed = "
        "normally open ties."
    )

with right:
    st.subheader("Switching decision")

    if best:
        st.write("**Close ties**")
        st.write(best.plan.close_ties or "No tie closures")

        st.write("**Open branches**")
        st.write(best.plan.open_branches or "No additional openings")

        st.write("**Restoration**")
        st.write(f"{best.plan.restoration_pct:.2f}%")

        st.write("**Maximum voltage**")
        st.write(
            f"{best.max_voltage_pu:.4f} pu"
            if best.max_voltage_pu is not None
            else "Unavailable"
        )

        st.write("**Thermal status**")
        st.warning(best.thermal_status)

    else:
        st.write("No electrically feasible candidate was found.")


# ---------------------------------------------------------
# Candidate comparison table and CSV
# ---------------------------------------------------------

st.subheader("Candidate comparison")

rows = []

for index, result in enumerate(results, start=1):
    rows.append(
        {
            "Rank": index,
            "Close ties": ", ".join(result.plan.close_ties) or "—",
            "Open branches": (
                ", ".join(result.plan.open_branches) or "—"
            ),
            "Restored kW": result.plan.restored_kw,
            "Restoration %": result.plan.restoration_pct,
            "Switching operations": result.plan.switching_operations,
            "Converged": result.converged,
            "Voltage feasible": result.voltage_feasible,
            "Graph consistent": result.graph_electrical_consistent,
            "Min voltage pu": result.min_voltage_pu,
            "Max voltage pu": result.max_voltage_pu,
            "Losses kW": result.real_losses_kw,
            "Thermal": result.thermal_status,
            "Rejection reason": result.rejection_reason or "—",
        }
    )

results_df = pd.DataFrame(rows)

st.dataframe(
    results_df,
    width="stretch",
    hide_index=True,
)

st.download_button(
    "Download results CSV",
    data=results_df.to_csv(index=False).encode("utf-8"),
    file_name="gtde_restoration_results.csv",
    mime="text/csv",
    width="stretch",
)

st.caption(
    "Decision support only. Thermal safety has not been verified "
    "because verified ampacity ratings are not available. Validate "
    "switching plans before any real-world operation."
)


# ---------------------------------------------------------
# Baseline versus adaptive comparison
# ---------------------------------------------------------

st.divider()
st.subheader("Baseline vs adaptive strategy comparison")

if st.button("Compare both strategies", width="stretch"):
    comparison_progress = st.progress(0)
    comparison_status = st.empty()

    try:
        comparison_status.write(
            "Running baseline and adaptive comparisons..."
        )

        comparison = compare_strategies(
            net,
            faulted_branches={active_fault},
            max_operations=max_operations,
            evaluation_budget=evaluation_budget,
            capacitor_bus=capacitor_bus,
            capacitor_kvar=capacitor_kvar,
        )

        comparison_df = pd.DataFrame(comparison)

        comparison_progress.progress(1.0)
        comparison_status.success("Strategy comparison finished.")

        st.dataframe(
            comparison_df,
            width="stretch",
            hide_index=True,
        )

        st.download_button(
            "Download strategy comparison CSV",
            data=comparison_df.to_csv(index=False).encode("utf-8"),
            file_name="gtde_strategy_comparison.csv",
            mime="text/csv",
            width="stretch",
        )

    except Exception as exc:
        comparison_status.error("Strategy comparison failed.")
        st.exception(exc)