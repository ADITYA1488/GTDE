
"""Thermal analysis using solved OpenDSS branch currents."""

from opendssdirect import dss

from src.thermal_limits import (
    check_branch_ampacity,
    feeder_thermal_status,
)


def extract_branch_currents_a():
    """Return maximum measured conductor current per enabled line.

    CurrentsMagAng returns alternating magnitude and angle values.
    """
    branch_currents = {}

    for line_name in dss.Lines.AllNames():
        if not line_name:
            continue

        dss.Lines.Name(line_name)

        if not dss.CktElement.Enabled():
            continue

        values = dss.CktElement.CurrentsMagAng()
        if not values:
            continue

        magnitudes = [
            float(value)
            for value in values[0::2]
        ]

        if magnitudes:
            branch_currents[line_name.upper()] = max(magnitudes)

    return branch_currents


def analyze_thermal_limits(ampacity_ratings_a):
    """Check measured currents against supplied verified ratings."""
    currents = extract_branch_currents_a()
    ratings = {
        key.upper(): value
        for key, value in ampacity_ratings_a.items()
    }

    results = [
        check_branch_ampacity(
            branch_id=branch_id,
            measured_current_a=current,
            ampacity_a=ratings.get(branch_id),
        )
        for branch_id, current in currents.items()
    ]

    return {
        "branch_count": len(currents),
        "thermal_status": feeder_thermal_status(results),
        "results": results,
    }
