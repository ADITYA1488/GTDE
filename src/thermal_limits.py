"""Thermal ampacity validation for distribution feeder branches.

Ratings must come from verified feeder data. Missing ratings are reported
as unassessed rather than assumed to be safe.
"""

from dataclasses import dataclass
from typing import Mapping, Optional


@dataclass(frozen=True)
class AmpacityResult:
    branch_id: str
    measured_current_a: Optional[float]
    ampacity_a: Optional[float]
    status: str
    margin_a: Optional[float]
    loading_pct: Optional[float]
    message: str


def check_branch_ampacity(
    branch_id: str,
    measured_current_a: Optional[float],
    ampacity_a: Optional[float],
    tolerance_a: float = 1e-6,
) -> AmpacityResult:
    """Check one branch current against its verified ampacity rating."""

    if measured_current_a is None or ampacity_a is None:
        return AmpacityResult(
            branch_id=branch_id,
            measured_current_a=measured_current_a,
            ampacity_a=ampacity_a,
            status="UNASSESSED",
            margin_a=None,
            loading_pct=None,
            message="Current or verified ampacity rating is missing.",
        )

    if measured_current_a < 0:
        raise ValueError("Measured current cannot be negative.")

    if ampacity_a <= 0:
        raise ValueError("Ampacity rating must be greater than zero.")

    if tolerance_a < 0:
        raise ValueError("Tolerance cannot be negative.")

    margin = ampacity_a - measured_current_a
    loading = 100.0 * measured_current_a / ampacity_a

    if measured_current_a > ampacity_a + tolerance_a:
        status = "VIOLATION"
        message = "Branch current exceeds its ampacity rating."
    else:
        status = "PASS"
        message = "Branch current is within its ampacity rating."

    return AmpacityResult(
        branch_id=branch_id,
        measured_current_a=measured_current_a,
        ampacity_a=ampacity_a,
        status=status,
        margin_a=margin,
        loading_pct=loading,
        message=message,
    )


def check_feeder_ampacity(
    branch_currents_a: Mapping[str, float],
    ampacity_ratings_a: Mapping[str, float],
) -> list[AmpacityResult]:
    """Validate all supplied branch currents.

    A missing rating is not treated as a passing thermal check.
    """

    results = []

    for branch_id, current in branch_currents_a.items():
        rating = ampacity_ratings_a.get(branch_id)

        results.append(
            check_branch_ampacity(
                branch_id=branch_id,
                measured_current_a=current,
                ampacity_a=rating,
            )
        )

    return results


def feeder_thermal_status(
    results: list[AmpacityResult],
) -> str:
    """Summarize thermal status without hiding missing data."""

    if any(result.status == "VIOLATION" for result in results):
        return "VIOLATION"

    if any(result.status == "UNASSESSED" for result in results):
        return "UNASSESSED"

    return "PASS"