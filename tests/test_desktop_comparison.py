import math

from dashboard.desktop_app import (
    comparison_results_equal,
    comparison_delta_text,
    comparison_status_text,
    format_comparison_value,
)


def make_row(strategy, **overrides):
    row = {
        "Strategy": strategy,
        "Candidates returned": 10,
        "Electrically feasible candidates": 4,
        "Fully verified candidates": 0,
        "Best graph-connected load (kW)": 3715.0,
        "Graph-connected restoration (%)": 100.0,
        "Minimum voltage (pu)": 0.9512872818,
        "Real losses (kW)": 113.7470649,
        "Switching operations": 3,
        "Thermal status": "UNASSESSED",
    }
    row.update(overrides)
    return row


def test_comparison_formatting_uses_requested_precision_and_missing_dash():
    assert format_comparison_value(3715, 1, " kW") == "3715.0 kW"
    assert format_comparison_value(0.951287, 4, " p.u.") == "0.9513 p.u."
    assert format_comparison_value(113.747, 2, " kW") == "113.75 kW"
    assert format_comparison_value(None, 2, " kW") == "—"
    assert format_comparison_value(math.nan, 2, " kW") == "—"
    assert format_comparison_value(math.inf, 4, " p.u.") == "—"


def test_equal_l10_style_rows_produce_concise_message_and_equal_deltas():
    baseline = make_row("baseline")
    adaptive = make_row("adaptive")
    assert comparison_results_equal([baseline, adaptive])
    assert comparison_status_text([baseline, adaptive]) == "No measurable difference between strategies for this scenario."
    assert comparison_delta_text(baseline["Real losses (kW)"], adaptive["Real losses (kW)"], 2, " kW") == "Equal in both strategies."
    assert format_comparison_value(baseline["Thermal status"], None) == "UNASSESSED"


def test_different_and_missing_results_are_reported_without_claiming_superiority():
    baseline = make_row("baseline", **{"Real losses (kW)": None, "Minimum voltage (pu)": math.nan})
    adaptive = make_row("adaptive", **{"Best graph-connected load (kW)": 3600.0, "Real losses (kW)": 120.0, "Minimum voltage (pu)": 0.94})
    assert not comparison_results_equal([baseline, adaptive])
    assert comparison_status_text([baseline, adaptive]).startswith("Measured outcomes differ:")
    assert comparison_delta_text(3715.0, 3600.0, 1, " kW") == "Adaptive − Baseline: −115.0 kW."
    assert comparison_delta_text(baseline["Real losses (kW)"], adaptive["Real losses (kW)"], 2, " kW") == "Delta unavailable (measurement missing)."
    assert format_comparison_value(baseline["Real losses (kW)"], 2, " kW") == "—"
    assert "superior" not in comparison_status_text([baseline, adaptive]).lower()
