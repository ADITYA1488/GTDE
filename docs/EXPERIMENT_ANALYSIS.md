# GTDE Experiment Analysis

## Experiment setup

GTDE evaluates restoration candidates for single-branch faults on a
synthetic six-bus distribution feeder.

- Total modeled load: 540 kW
- Maximum switching operations: 3
- Search results evaluated electrically: 244 candidates
- Candidates passing the current feasibility filters: 32
- Fault scenarios with feasible candidates: L23, L34, L45, L56

## Feasibility filters

Candidates are classified as feasible when:

1. OpenDSS converges.
2. Minimum bus voltage is at least 0.95 pu.
3. Maximum bus voltage is at most 1.05 pu.
4. No modeled load remains unsupplied.
5. Real power losses are non-negative.
6. The graph topology passes the existing validation.

These filters are prototype screening criteria, not complete grid
operational or safety constraints.

## Results

### Lowest-loss candidates

| Fault | Tie closures | Branch opened | Restored load | Operations | Real losses |
|---|---|---|---:|---:|---:|
| L23 | T25, T36 | L34 | 100% | 3 | 1.105425 kW |
| L34 | T25, T36 | L56 | 100% | 3 | 0.684293 kW |
| L45 | T25, T36 | L56 | 100% | 3 | 0.666513 kW |
| L56 | T25, T36 | L45 | 100% | 3 | 0.666513 kW |

### Fewest-operation candidates with full restoration

| Fault | Tie closure | Branch opened | Restored load | Operations | Real losses |
|---|---|---|---:|---:|---:|
| L23 | T25 | L34 | 100% | 1 | 1.117003 kW |
| L34 | T25 | L56 | 100% | 1 | 0.765497 kW |
| L45 | T25 | None | 100% | 1 | 0.680589 kW |
| L56 | T36 | L45 | 100% | 1 | 0.954916 kW |

## Interpretation

For the L45 fault, the three-operation candidate has modeled real
losses of 0.666513 kW, compared with 0.680589 kW for the one-operation
candidate. This is approximately a 2.07% reduction in modeled losses
at the cost of two additional switching operations.

The appropriate choice depends on the relative importance of losses,
switching effort, and operational constraints.

## Limitations

The feeder and line parameters are synthetic. The search is bounded,
and the results describe candidates returned by this implementation,
not every possible network configuration. Reactive-loss results
require further investigation. No protection coordination, thermal
limits, fault-current study, or field validation is included.

The results must not be used as real-world switching instructions.