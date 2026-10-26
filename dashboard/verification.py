"""Shared dashboard eligibility rules for restoration results."""

from src.restoration_reporting import (
    classify_candidates,
    is_fully_verified,
    passes_electrical_checks,
)


def thermal_unassessed_electrical_candidates(results):
    """Return electrically feasible candidates with no thermal assessment."""
    return [
        result
        for result in results
        if passes_electrical_checks(result)
        and result.thermal_status == "UNASSESSED"
    ]


def candidate_summary(results):
    """Summarize eligibility without changing the incoming ranking order."""
    groups = classify_candidates(results)
    fully_verified = groups["fully_verified"]
    electrically_feasible = groups["electrically_feasible"]
    provisional = not fully_verified and bool(electrically_feasible)
    selected = (
        fully_verified[0]
        if fully_verified
        else electrically_feasible[0]
        if electrically_feasible
        else None
    )
    return {
        "fully_verified": fully_verified,
        "electrically_feasible": electrically_feasible,
        "thermal_unassessed": thermal_unassessed_electrical_candidates(results),
        "selected": selected,
        "provisional": provisional,
    }
