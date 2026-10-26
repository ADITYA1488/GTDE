"""Shared result-eligibility rules used by dashboards and reports."""


def passes_electrical_checks(result):
    """Return whether convergence, voltage, and graph checks all pass."""
    return bool(
        result.converged
        and result.voltage_feasible
        and result.graph_electrical_consistent
    )


def is_fully_verified(result):
    """Full verification requires electrical checks and thermal PASS."""
    return passes_electrical_checks(result) and result.thermal_status == "PASS"


def classify_candidates(results):
    """Return explicit electrical and full-verification candidate groups."""
    electrically_feasible = [
        result for result in results if passes_electrical_checks(result)
    ]
    fully_verified = [
        result for result in electrically_feasible
        if result.thermal_status == "PASS"
    ]
    return {
        "electrically_feasible": electrically_feasible,
        "fully_verified": fully_verified,
    }


def add_combined_benchmark_fields(row):
    """Add explicit aliases to the combined benchmark while keeping legacy keys."""
    row["graph_connected_load_kw"] = row.get("load_served_kw")
    row["graph_connected_load_pct"] = row.get("load_served_pct")
    row["electrically_feasible"] = bool(row.get("feasible", False))
    row["fully_verified"] = bool(
        row.get("powerflow_converged") is True
        and row.get("voltage_feasible") is True
        and row.get("graph_electrical_consistent") is True
        and row.get("thermal_status") == "PASS"
    )
    row["fully_assessed_feasible"] = row["fully_verified"]
    return row
