
"""Explicit lexicographic ranking for restoration candidates."""

def restoration_rank(result):
    """
    Return verification-first ordering as a lower-is-better tuple.

    Fully verified candidates rank first, followed by greater priority-
    weighted served load, greater raw graph-connected load, lower real losses
    (missing losses rank last), and fewer switching operations. Bus priority
    metadata defaults to equal weights, preserving the existing ordering when
    it is absent.
    """
    fully_verified = (
        result.converged
        and result.voltage_feasible
        and result.graph_electrical_consistent
        and result.thermal_status == "PASS"
    )

    restored_kw = result.plan.restored_kw
    priority_score = getattr(result.plan, "priority_load_score", None)
    priority_score = (
        0.0 if priority_score is None else float(priority_score)
    )
    losses_kw = result.real_losses_kw
    operations = result.plan.switching_operations

    return (
        0 if fully_verified else 1,
        -priority_score,
        -restored_kw,
        losses_kw if losses_kw is not None else float("inf"),
        operations,
    )
