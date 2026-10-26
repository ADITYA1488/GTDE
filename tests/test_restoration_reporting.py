import csv
from pathlib import Path
from types import SimpleNamespace

import src.strategy_comparison as strategy_comparison
from dashboard.verification import candidate_summary
from src.restoration_reporting import (
    add_combined_benchmark_fields,
    classify_candidates,
)


ROOT = Path(__file__).resolve().parents[1]


def make_result(
    *, converged=True, voltage=True, graph=True, thermal="UNASSESSED",
    restored=3715.0, percent=100.0, losses=120.0,
):
    return SimpleNamespace(
        converged=converged,
        voltage_feasible=voltage,
        graph_electrical_consistent=graph,
        thermal_status=thermal,
        real_losses_kw=losses,
        min_voltage_pu=0.94 if not voltage else 0.96,
        max_voltage_pu=1.0,
        plan=SimpleNamespace(
            restored_kw=restored,
            restoration_pct=percent,
            switching_operations=2,
        ),
    )


def test_candidate_classification_requires_voltage_and_thermal_pass():
    voltage_fail = make_result(voltage=False, thermal="PASS")
    convergence_fail = make_result(converged=False, thermal="PASS")
    graph_fail = make_result(graph=False, thermal="PASS")
    thermal_unassessed = make_result(thermal="UNASSESSED")
    verified = make_result(thermal="PASS")

    groups = classify_candidates([
        voltage_fail, convergence_fail, graph_fail, thermal_unassessed, verified
    ])

    assert groups["electrically_feasible"] == [thermal_unassessed, verified]
    assert groups["fully_verified"] == [verified]


def test_voltage_infeasible_candidates_are_not_selected_or_provisional():
    summary = candidate_summary([make_result(voltage=False)])

    assert summary["selected"] is None
    assert summary["provisional"] is False
    assert summary["fully_verified"] == []


def test_strategy_report_separates_electrical_and_full_verification(monkeypatch):
    results = [
        make_result(voltage=False, thermal="PASS", losses=1.0),
        make_result(thermal="UNASSESSED", losses=2.0),
        make_result(thermal="PASS", losses=3.0),
    ]
    monkeypatch.setattr(
        strategy_comparison,
        "evaluate_restoration_plans",
        lambda *args, **kwargs: results,
    )

    rows = strategy_comparison.compare_strategies(None, {"L10"})

    assert len(rows) == 2
    for row in rows:
        assert row["Electrically feasible candidates"] == 2
        assert row["Fully verified candidates"] == 1
        assert row["Best graph-connected load (kW)"] == 3715.0
        assert row["Thermal status"] == "UNASSESSED"
        assert "Best restored load (kW)" not in row


def test_combined_benchmark_adds_explicit_fields_without_changing_legacy_values():
    row = {
        "load_served_kw": 3715.0,
        "load_served_pct": 100.0,
        "feasible": True,
        "thermal_status": "UNASSESSED",
        "fully_assessed_feasible": False,
        "powerflow_converged": True,
        "voltage_feasible": True,
        "graph_electrical_consistent": True,
        "verification_scope": "topology and electrical checks plus thermal PASS",
    }

    add_combined_benchmark_fields(row)

    assert row["load_served_kw"] == row["graph_connected_load_kw"] == 3715.0
    assert row["load_served_pct"] == row["graph_connected_load_pct"] == 100.0
    assert row["feasible"] is True
    assert row["electrically_feasible"] is True
    assert row["fully_verified"] is False
    assert row["fully_assessed_feasible"] is False
    assert row["verification_scope"] == "topology and electrical checks plus thermal PASS"


def test_combined_benchmark_does_not_fully_verify_voltage_failure():
    row = {
        "load_served_kw": 3715.0,
        "load_served_pct": 100.0,
        "feasible": False,
        "powerflow_converged": True,
        "voltage_feasible": False,
        "graph_electrical_consistent": True,
        "thermal_status": "PASS",
    }

    add_combined_benchmark_fields(row)

    assert row["electrically_feasible"] is False
    assert row["fully_verified"] is False


def test_combined_benchmark_requires_thermal_pass_after_electrical_checks():
    row = {
        "load_served_kw": 3715.0,
        "load_served_pct": 100.0,
        "feasible": True,
        "powerflow_converged": True,
        "voltage_feasible": True,
        "graph_electrical_consistent": True,
        "thermal_status": "PASS",
    }

    add_combined_benchmark_fields(row)

    assert row["electrically_feasible"] is True
    assert row["fully_verified"] is True


def test_combined_benchmark_rejects_composite_feasibility_without_graph_consistency():
    row = {
        "feasible": True,
        "powerflow_converged": True,
        "voltage_feasible": True,
        "graph_electrical_consistent": False,
        "thermal_status": "PASS",
    }

    add_combined_benchmark_fields(row)

    assert row["electrically_feasible"] is True
    assert row["fully_verified"] is False


def test_combined_benchmark_unassessed_thermal_is_not_fully_verified():
    row = {
        "feasible": True,
        "powerflow_converged": True,
        "voltage_feasible": True,
        "graph_electrical_consistent": True,
        "thermal_status": "UNASSESSED",
    }

    add_combined_benchmark_fields(row)

    assert row["fully_verified"] is False


def test_combined_benchmark_requires_graph_consistency_to_be_boolean_true():
    values = [
        (True, True),
        (False, False),
        ("True", False),
        ("False", False),
        (None, False),
        ("", False),
        ("UNKNOWN", False),
        ("yes", False),
    ]

    for consistency, expected in values:
        row = {
            "powerflow_converged": True,
            "voltage_feasible": True,
            "graph_electrical_consistent": consistency,
            "thermal_status": "PASS",
        }

        add_combined_benchmark_fields(row)

        assert row["fully_verified"] is expected


def test_combined_benchmark_missing_graph_consistency_is_not_fully_verified():
    row = {
        "powerflow_converged": True,
        "voltage_feasible": True,
        "thermal_status": "PASS",
    }

    add_combined_benchmark_fields(row)

    assert row["fully_verified"] is False


def test_saved_benchmark_csvs_keep_legacy_fields_and_add_explicit_fields():
    expected = {
        "results/ieee33_benchmark.csv": {
            "feasible", "restored_kw", "electrically_feasible_candidates",
            "fully_verified_candidates", "graph_connected_load_kw",
            "graph_connected_restoration_pct", "feasibility_scope",
            "verification_scope", "capacitor_bus", "capacitor_kvar",
        },
        "results/combined_optimization_benchmark.csv": {
            "feasible", "load_served_kw", "load_served_pct",
            "electrically_feasible", "fully_verified",
            "graph_connected_load_kw", "graph_connected_load_pct",
            "verification_scope", "graph_electrical_consistent",
        },
    }

    for relative_path, required_fields in expected.items():
        with (ROOT / relative_path).open(newline="", encoding="utf-8") as file:
            reader = csv.DictReader(file)
            header = set(reader.fieldnames or [])
            rows = list(reader)
        assert required_fields <= header
        if relative_path.endswith("ieee33_benchmark.csv"):
            for row in rows:
                assert row["graph_connected_load_kw"] == row["restored_kw"]
                assert row["graph_connected_restoration_pct"] == row["restoration_pct"]
                assert row["capacitor_bus"] == "33"
                assert row["capacitor_kvar"] == "900"
                if row["thermal_status"] == "UNASSESSED":
                    assert row["fully_verified_candidates"] in {"0", ""}
        else:
            for row in rows:
                assert row["graph_connected_load_kw"] == row["load_served_kw"]
                assert row["graph_connected_load_pct"] == row["load_served_pct"]
                # Historical output predates the explicit bus-set check, so
                # leave the added field blank rather than infer consistency.
                assert row["graph_electrical_consistent"] == ""
                assert row["electrically_feasible"] == row["feasible"]
                assert row["fully_verified"] == row["fully_assessed_feasible"]
                if row["thermal_status"] == "UNASSESSED":
                    assert row["fully_verified"] == "False"
