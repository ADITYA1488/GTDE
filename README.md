# GridResQ

## Graph-Based Distribution Feeder Reconfiguration and Constraint-Aware Outage Restoration

GridResQ is a Python research prototype for studying distribution-feeder fault restoration. A feeder fault can disconnect downstream buses even when their lines are not themselves damaged. GridResQ removes the faulted branch from the model, searches for switching plans that reconnect source-disconnected load while preserving radial topology, and evaluates a bounded set of candidate plans with OpenDSS.

The project supports the IEEE 33-bus test feeder. Its goal is to make restoration candidates and their electrical results inspectable; it is not a utility control system or a validated operating plan.

## What the application evaluates

For each candidate, GridResQ reports:

- OpenDSS convergence.
- Minimum and maximum voltage against the configured **0.95–1.05 p.u.** limits.
- Graph/electrical consistency, by comparing graph-supplied buses with OpenDSS-energized buses.
- Graph-connected load, switching operations, and real-power losses.
- Thermal status, which is `UNASSESSED` when verified ampacity ratings are unavailable.

Electrical feasibility requires convergence, voltage compliance, and graph/electrical consistency. **Fully verified** additionally requires thermal status exactly `PASS`. Ranking a candidate does not itself establish feasibility or verification.

“Graph-connected load” is the modeled demand at source-connected buses. It does not prove that the load is served while satisfying voltage limits. Do not interpret this quantity as voltage-compliant served load when voltage compliance fails or is unknown.

## Architecture and data flow

1. `src/ieee33_electrical_data.py` holds the feeder bus, load, branch-impedance, source, and tie data. `src/ieee33_network.py` builds the network model used by the planner and visualization.
2. `src/restoration.py` removes faulted branches from the active graph, identifies disconnected buses, builds BFS recovery paths, generates bounded switching candidates, and checks radial topology.
3. `src/restoration_powerflow.py` deduplicates candidate topologies, retains a bounded shortlist, evaluates candidates, and compares graph-supplied buses with the buses energized by OpenDSS.
4. `src/ieee33_powerflow.py` builds and solves the IEEE-33 OpenDSS circuit, then returns convergence, voltage, energized-bus, and real-loss metrics. Thermal analysis can compare extracted branch currents with supplied ratings.
5. `src/restoration_reporting.py` applies the shared electrical-feasibility and strict full-verification criteria. `src/restoration_objectives.py` supplies the candidate ordering.
6. `dashboard/app.py` presents the interactive Streamlit demonstration. It uses `dashboard/topology.py` for model-derived plot data and calls the existing evaluator through `dashboard/evaluation_runner.py` and `dashboard/evaluation_worker.py`; it does not implement a second restoration search.
7. `benchmark_ieee33.py` evaluates six fault locations using baseline and adaptive strategies and writes its CSV to `GRIDRESQ_RESULTS_DIR` (default: `results/`).

The planner and OpenDSS evaluator are distinct checks: graph connectivity and radiality do not substitute for electrical evaluation.

## Requirements and setup

The checked repository environment uses Python 3.12.6. Core dependencies are declared in `requirements.txt`: NetworkX, pandas, Plotly, Streamlit, OpenDSSDirect.py, and pytest. On Windows, from the repository root in PowerShell:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

To use the optional PySide6 desktop interface, install its dependency separately (it is not listed in `requirements.txt`):

```powershell
.\.venv\Scripts\python.exe -m pip install PySide6
.\.venv\Scripts\python.exe -m dashboard.desktop_app
```

## Launch the interactive dashboard

From the repository root:

```powershell
.\.venv\Scripts\python.exe -m streamlit run dashboard/app.py
```

Streamlit prints the local URL after startup. In the sidebar, select a supported main-branch fault (the default is L10), choose the network view, and optionally inspect a bus. Set the switching-operation limit, OpenDSS evaluation budget, capacitor support, and search strategy, then click **Run restoration**. Select a candidate to inspect its switching actions and diagnostics. The topology view can show the pre-fault, post-fault, or candidate-restoration state.

Use **Compare both strategies** to run baseline and adaptive evaluation on the same selected fault and budget. The dashboard reports measured differences; identical results are not evidence of adaptive improvement. Use **Download results CSV** to export the current dashboard results. The export is generated in memory and does not overwrite the benchmark CSV.

The default dashboard capacitor setting is **900 kVAr at bus 33**. Disable the checkbox for a no-capacitor run. Keep results from these configurations separate when interpreting them.

## Tests

Run the project regression suite with its virtual environment:

```powershell
.\.venv\Scripts\python.exe -c "import opendssdirect; import pytest; raise SystemExit(pytest.main(['tests/', '-q']))"
```

**Latest full suite run (2026-10-26):** 78 tests passed in 5.96 seconds (exit code 0). Duration is specific to that run, not a stable performance metric.

## IEEE-33 benchmark

The benchmark evaluates faults L05, L10, L15, L20, L25, and L30 with a maximum of three switching operations and an OpenDSS evaluation budget of ten. It compares `baseline` and `adaptive`, with **900 kVAr capacitor support at bus 33**. It reports candidate counts, electrical-feasibility and full-verification counts, graph-connected load, losses, minimum voltage, switching actions, thermal status, and runtime.

The script writes `ieee33_benchmark.csv` into the directory named by `GRIDRESQ_RESULTS_DIR`. Directing output to a fresh temporary directory avoids replacing `results/ieee33_benchmark.csv`:

```powershell
$env:GRIDRESQ_RESULTS_DIR = Join-Path $env:TEMP 'gridresq_ieee33_release_run'
.\.venv\Scripts\python.exe benchmark_ieee33.py
```

Choose a new, empty directory name for each run. The script writes to the configured directory and can replace a CSV already there.

### Validated benchmark observations

The release-pass benchmark used a new temporary output directory. With the 900 kVAr bus-33 configuration, baseline and adaptive produced identical measured outcomes for the six tested faults. Each strategy evaluated ten candidates per fault; electrically feasible counts were 0 for L05, 4 for L10, 0 for L15, 0 for L20, 2 for L25, and 4 for L30. The best electrically feasible loss/minimum-voltage results were 113.747 kW/0.9513 p.u. for L10, 121.586 kW/0.9507 p.u. for L25, and 156.509 kW/0.9514 p.u. for L30. All scenarios had zero fully verified candidates because thermal status was `UNASSESSED`. No adaptive outcome improvement was demonstrated.

A separate no-capacitor diagnostic used a ten-candidate evaluation budget and three-switching-operation limit. Its baseline minimum voltage was **0.916109 p.u. at bus 18**. Across ten candidates each for L04, L05, L10, and L20, all 40 converged and passed graph/electrical consistency, but all failed voltage compliance. This no-capacitor diagnostic is distinct from the 900 kVAr bus-33 benchmark.

## Research-method alignment

The statuses below describe method-level overlap only. They do not indicate a percentage of paper reproduction. GridResQ does not reproduce either paper in full.

| Paper method | Status | GridResQ implementation and gap |
|---|---|---|
| Peng et al. (2024): BFS-based graph traversal | PARTIAL | BFS is used for source-connected outage/recovery-path analysis. The paper uses DFS/BFS for island partitioning and DFS adjustment; GridResQ does not form self-sufficient DG islands. |
| Peng et al. (2024): critical-load priority, network losses, and switch-operation criteria | PARTIAL | Optional bus priority metadata and bounded candidate ranking exist. GridResQ does not implement the paper’s complete weighted islanding/reconfiguration objective. |
| Peng et al. (2024): CVaR risk treatment of uncertain distributed generation, including scenario generation/reduction | MISSING | There is no stochastic DER-output model, CVaR objective, Latin-hypercube scenario generation, or K-means scenario reduction. |
| Peng et al. (2024): distributed-generation island power balance | MISSING | The current feeder has a single modeled source and no dispatchable DG island model. |
| Peng et al. (2024): branch ampacity constraint | PARTIAL | `src/thermal_limits.py` can compare measured current with supplied ratings, but authoritative ratings are not configured for this feeder; thermal results remain `UNASSESSED`. |
| Peng et al. (2024) and Chen et al. (2025): radial topology and switching constraints | PARTIAL | GridResQ checks radiality and bounds switching operations, but uses its own bounded graph search rather than either paper’s optimization formulation. |
| Chen et al. (2025): topology reconfiguration with linearized DistFlow power-flow constraints | PARTIAL | GridResQ evaluates candidates using OpenDSS and voltage limits. It does not implement the paper’s linearized DistFlow optimization model. |
| Chen et al. (2025): DER scheduling, load-shedding optimization, multiple networked microgrids, and fairness cases | MISSING | These resources, schedules, and operating scenarios are not modeled in this single-source IEEE-33 prototype. |
| Chen et al. (2025): hardware-in-the-loop validation | MISSING | No HIL equipment, controller integration, or real-time HIL experiment is included. |

The bounded tie-switch search, graph/electrical bus-set consistency check, OpenDSS evaluation pipeline, and interactive dashboard are GridResQ design choices; their presence alone does not constitute implementation of a paper’s full method.

References: [Peng et al. (2024), DOI 10.3389/fenrg.2024.1460894](https://www.frontiersin.org/journals/energy-research/articles/10.3389/fenrg.2024.1460894/full); [Chen et al. (2025), DOI 10.1109/ACCESS.2025.3527329](https://doi.org/10.1109/ACCESS.2025.3527329).

## Limitations and interpretation

- Thermal compliance is **`UNASSESSED`** because authoritative ampacity ratings are unavailable. OpenDSS branch-current measurements alone do not establish thermal compliance. Verified ampacity values and a documented mapping to every modeled branch/tie are required before this check can report `PASS`.
- A candidate with voltage violations is not electrically feasible even if the planner reports all graph-connected load.
- The benchmark comparison did not demonstrate better evaluated outcomes for the adaptive strategy.
- Search is bounded and tests a limited candidate set; results depend on the modeled feeder, switching limits, candidate budget, and OpenDSS configuration.
- The comparison with Peng et al. and Chen et al. is methodological context, not exact reproduction. There is no physical feeder validation or hardware-in-the-loop validation.
- GridResQ is a simulation-based research prototype. Its outputs are not direct switching instructions and do not replace protection coordination, utility procedures, or engineering approval.
