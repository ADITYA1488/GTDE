"""GTDE: Graph-Theory Driven Feeder Reconfiguration and Restoration."""

import streamlit as st
import pandas as pd
import plotly.express as px

from src.ieee33_network import build_ieee33_network
from dashboard.evaluation_runner import (
    compare_restoration_strategies,
    evaluate_restoration,
)
from dashboard.verification import (
    candidate_summary,
    is_fully_verified,
    passes_electrical_checks,
)
from dashboard.topology import (
    VIEWS, build_feeder_figure, candidate_label, select_candidate,
    supported_faults,
)


st.set_page_config(
    page_title="GridResQ | Feeder Restoration",
    page_icon="⚡",
    layout="wide",
)

st.title("⚡ GridResQ — Feeder Restoration")
st.caption(
    "IEEE 33-bus | Graph-based FLISR | OpenDSS electrical validation"
)


@st.cache_resource
def load_network():
    return build_ieee33_network()


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

    fault_options = supported_faults(net)
    fault = st.selectbox(
        "Fault scenario (main branch)", fault_options,
        index=fault_options.index("L10") if "L10" in fault_options else 0,
    )

    topology_view = st.selectbox("Network state", VIEWS, index=0)
    selected_bus = st.selectbox("Inspect bus", sorted(net.buses), index=0)
    bus_info = net.buses[selected_bus]
    st.caption(
        f"{bus_info.get('name', f'Bus {selected_bus}')} · "
        f"{float(bus_info.get('load_kw', 0)):.1f} kW demand · "
        f"priority weight {bus_info.get('load_priority_weight', 1.0)}"
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
    st.caption(
        f"Capacitor configuration: {capacitor_kvar} kVAr"
        + (f" at bus {capacitor_bus}" if capacitor_bus is not None else " (disabled)")
    )

    run = st.button(
        "Run restoration",
        type="primary",
        width="stretch",
    )

run_signature = (
    fault, strategy, max_operations, evaluation_budget,
    capacitor_bus, capacitor_kvar,
)


# ---------------------------------------------------------
# Run restoration with visible progress
# ---------------------------------------------------------

if run:
    st.session_state.pop("gtde_results", None)
    st.session_state.pop("gtde_fault", None)

    progress = st.progress(0)
    status = st.empty()

    try:
        status.write(
            "Generating graph-valid plans and running the bounded OpenDSS "
            "evaluation in an isolated worker..."
        )
        results = evaluate_restoration(
            faulted_branches={fault},
            max_operations=max_operations,
            max_results=10,
            capacitor_bus=capacitor_bus,
            capacitor_kvar=capacitor_kvar,
            max_electrical_evaluations=evaluation_budget,
            strategy=strategy,
        )

        st.session_state["gtde_results"] = results
        st.session_state["gtde_fault"] = fault
        st.session_state["gtde_strategy"] = strategy
        st.session_state["gtde_signature"] = run_signature

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
if st.session_state.get("gtde_signature") != run_signature:
    results = []

if not results:
    st.info("Choose simulation settings and click Run restoration.")
    st.plotly_chart(build_feeder_figure(
        net, faulted_branches={fault}, view=topology_view,
        selected_bus=selected_bus,
    ), width="stretch")
    current_state = "pre-fault" if topology_view == "Pre-fault" else "post-fault"
    st.caption(f"Showing {current_state} topology. Grey buses are disconnected in this state; select a bus in the sidebar to inspect demand.")
    st.stop()


candidate_index = st.selectbox(
    "Candidate plan",
    options=range(len(results)),
    format_func=lambda index: candidate_label(index, results[index]),
    key="gtde_candidate_index",
)
selected_candidate = select_candidate(results, candidate_index)

summary = candidate_summary(results)
fully_verified = summary["fully_verified"]
electrically_feasible = summary["electrically_feasible"]
best = summary["selected"]

st.subheader("Restoration overview")

c1, c2, c3, c4, c5 = st.columns(5)

c1.metric(
    "Fully verified candidates",
    f"{len(fully_verified)} / {len(results)}",
)

c2.metric(
    "Electrical checks pass; thermal UNASSESSED",
    f"{len(summary['thermal_unassessed'])} / {len(results)}",
)

c3.metric(
    "Selected candidate graph-connected load",
    f"{selected_candidate.plan.restored_kw:,.1f} kW",
)
st.caption(
    "Graph-connected load is the demand at source-connected buses; it does not "
    "necessarily represent voltage-compliant served load."
)

c4.metric(
    "Selected candidate minimum voltage",
    (
        f"{selected_candidate.min_voltage_pu:.4f} pu"
        if selected_candidate.min_voltage_pu is not None
        else "—"
    ),
)

c5.metric(
    "Selected candidate real losses",
    (
        f"{selected_candidate.real_losses_kw:.3f} kW"
        if selected_candidate.real_losses_kw is not None
        else "—"
    ),
)

if best:
    if summary["provisional"]:
        st.warning(
            f"Provisional recommendation (electrically feasible): close "
            f"{best.plan.close_ties or 'none'}; open "
            f"{best.plan.open_branches or 'none'}. "
            + (
                "Thermal compliance is unverified; do not treat this plan as fully validated."
                if best.thermal_status == "UNASSESSED"
                else f"Thermal status is {best.thermal_status}; do not treat this plan as fully validated."
            )
        )
    else:
        st.success(
            f"Selected fully verified candidate: close "
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
    expanded=not bool(electrically_feasible),
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
                "Electrical checks pass": passes_electrical_checks(result),
                "Fully verified": is_fully_verified(result),
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
        "Electrical checks require convergence, voltage compliance, and graph consistency. "
        "Full verification additionally requires thermal PASS."
    )


# ---------------------------------------------------------
# Topology and switching decision
# ---------------------------------------------------------

left, right = st.columns([1.4, 1])

with left:
    st.subheader("Feeder topology")

    st.plotly_chart(build_feeder_figure(
        net, faulted_branches={active_fault}, plan=selected_candidate.plan,
        view=topology_view, selected_bus=selected_bus,
    ), width="stretch")

    st.caption(
        "Topology comes from the network model. Purple = candidate recovery path; "
        "green = candidate tie closure; orange = candidate opening; red = fault; "
        "blue dashed = normally open tie; grey buses = source-disconnected. "
        f"Voltage feasibility uses 0.95–1.05 p.u. Current view: {topology_view}."
    )

with right:
    st.subheader("Switching decision")

    if selected_candidate:
        st.write(f"**Candidate {candidate_index + 1} diagnostics**")
        st.write(f"Converged: {selected_candidate.converged}")
        st.write(f"Voltage compliant: {selected_candidate.voltage_feasible}")
        st.write(f"Graph/electrical consistent: {selected_candidate.graph_electrical_consistent}")
        st.write(f"Minimum voltage: {selected_candidate.min_voltage_pu:.4f} p.u." if selected_candidate.min_voltage_pu is not None else "Minimum voltage: unavailable")
        st.write(f"Maximum voltage: {selected_candidate.max_voltage_pu:.4f} p.u." if selected_candidate.max_voltage_pu is not None else "Maximum voltage: unavailable")
        st.write(f"Real losses: {selected_candidate.real_losses_kw:.3f} kW" if selected_candidate.real_losses_kw is not None else "Real losses: unavailable")
        st.write(f"Thermal status: {selected_candidate.thermal_status}")
        st.write(f"Fully verified: {is_fully_verified(selected_candidate)}")
        st.write(f"Graph-connected load: {selected_candidate.plan.restored_kw:.1f} kW")
        st.write(f"Switching operations: {selected_candidate.plan.switching_operations}")
        st.write("**Switching operations**")
        st.write(f"Close: {selected_candidate.plan.close_ties or 'none'} · Open: {selected_candidate.plan.open_branches or 'none'}")
        if not passes_electrical_checks(selected_candidate):
            st.warning("This candidate fails at least one electrical check and is not an eligible recommendation.")
    else:
        st.write("No evaluated candidate is selected.")

    if best:
        st.write("**Close ties**")
        st.write(best.plan.close_ties or "No tie closures")

        st.write("**Open branches**")
        st.write(best.plan.open_branches or "No additional openings")

        st.write("**Graph-connected restoration**")
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
        st.write("No candidate passed all electrical checks. No recommendation is available.")


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
            "Graph-connected load (kW)": result.plan.restored_kw,
            "Graph-connected restoration (%)": result.plan.restoration_pct,
            "Switching operations": result.plan.switching_operations,
            "Converged": result.converged,
            "Voltage feasible": result.voltage_feasible,
            "Graph consistent": result.graph_electrical_consistent,
            "Electrical checks pass": passes_electrical_checks(result),
            "Fully verified": is_fully_verified(result),
            "Min voltage pu": result.min_voltage_pu,
            "Max voltage pu": result.max_voltage_pu,
            "Losses kW": result.real_losses_kw,
            "Thermal": result.thermal_status,
            "Rejection reason": result.rejection_reason or "—",
        }
    )

results_df = pd.DataFrame(rows)
export_df = results_df.assign(
    **{
        "Fault scenario": active_fault,
        "Search strategy": st.session_state.get("gtde_strategy", strategy),
        "Capacitor bus": capacitor_bus,
        "Capacitor kVAr": capacitor_kvar,
    }
)

st.dataframe(
    results_df,
    width="stretch",
    hide_index=True,
)

st.download_button(
    "Download results CSV",
    data=(
        export_df.assign(
            **{
                # Keep historical CSV fields while adding explicit aliases.
                "Restored kW": results_df["Graph-connected load (kW)"],
                "Restoration %": results_df["Graph-connected restoration (%)"],
            }
        ).to_csv(index=False).encode("utf-8")
    ),
    file_name="gtde_restoration_results.csv",
    mime="text/csv",
    width="stretch",
)

st.caption(
    "Decision support only. Thermal safety has not been verified "
    "because verified ampacity ratings are not available. Validate "
    "switching plans before any real-world operation."
)

st.subheader("Candidate outcome comparison")
if not results_df.empty:
    chart_df = results_df[["Rank", "Graph-connected load (kW)", "Min voltage pu", "Max voltage pu", "Losses kW"]].melt(
        id_vars="Rank", var_name="Metric", value_name="Value"
    )
    st.plotly_chart(
        px.bar(
            chart_df, x="Rank", y="Value", color="Metric", barmode="group",
            facet_row="Metric", height=560,
        ), width="stretch",
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

        comparison = compare_restoration_strategies(
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

        outcome_columns = [
            "Candidates returned", "Electrically feasible candidates",
            "Fully verified candidates", "Best graph-connected load (kW)",
            "Graph-connected restoration (%)", "Minimum voltage (pu)",
            "Real losses (kW)", "Switching operations", "Thermal status",
        ]
        baseline_row = comparison_df.loc[comparison_df["Strategy"] == "baseline"].iloc[0]
        adaptive_row = comparison_df.loc[comparison_df["Strategy"] == "adaptive"].iloc[0]
        equal_outcomes = all(
            baseline_row[column] == adaptive_row[column]
            for column in outcome_columns
        )
        if equal_outcomes:
            st.info("Baseline and adaptive produced the same measured outcomes for this scenario and budget. Runtime is reported separately and is not an outcome improvement claim.")
        else:
            st.info("Baseline and adaptive differ on the measured outcomes shown below. These are scenario-specific results, not a general performance guarantee.")

        chart_columns = [
            "Electrically feasible candidates", "Fully verified candidates",
            "Best graph-connected load (kW)", "Minimum voltage (pu)",
            "Real losses (kW)", "Runtime (s)",
        ]
        comparison_chart = comparison_df.melt(
            id_vars="Strategy", value_vars=chart_columns,
            var_name="Measured metric", value_name="Value",
        )
        st.plotly_chart(
            px.bar(comparison_chart, x="Strategy", y="Value", color="Strategy", facet_row="Measured metric", height=680),
            width="stretch",
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
