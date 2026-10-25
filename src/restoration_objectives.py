
"""Explicit lexicographic ranking for restoration candidates."""

def restoration_rank(result):
    """
    Return the original restoration ordering as a lower-is-better tuple.

    Fully verified candidates rank first, followed by greater
    graph-connected load, lower real losses (missing losses rank last),
    and fewer switching operations.
    """
    fully_verified = (
        result.converged
        and result.voltage_feasible
        and result.graph_electrical_consistent
        and result.thermal_status == "PASS"
    )

    restored_kw = result.plan.restored_kw
    losses_kw = result.real_losses_kw
    operations = result.plan.switching_operations

    return (
        0 if fully_verified else 1,
        -restored_kw,
        losses_kw if losses_kw is not None else float("inf"),
        operations,
    )
