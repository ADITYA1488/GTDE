# GridResQ
### Graph-Based Distribution Feeder Reconfiguration and Constraint-Aware Outage Restoration

GridResQ is a software prototype for distribution feeder reconfiguration and outage restoration. It combines graph-theoretic switching-plan search with electrical power-flow evaluation to analyze candidate configurations following feeder faults.

The engine evaluates network topology, restoration potential, voltage constraints, and power losses. It also incorporates branch-current-based thermal analysis, with thermal compliance reported as unassessed when verified conductor ampacity ratings are unavailable.

## Key Features

- **IEEE 33-bus feeder:** Distribution network modeling and benchmark evaluation.
- **Fault simulation:** Analyze restoration scenarios involving faulted branches.
- **Graph-based search:** Generate candidate switching plans subject to switching-operation limits.
- **Topology validation:** Check radiality and graph/electrical consistency.
- **Power-flow simulation:** Evaluate candidate configurations using OpenDSS through OpenDSSDirect.py.
- **Voltage constraint checking:** Assess bus voltages against configurable operating limits.
- **Restoration analysis:** Calculate restored load and evaluate candidate restoration configurations.
- **Loss evaluation:** Compare real-power losses across candidates.
- **Adaptive strategy comparison:** Evaluate baseline and adaptive restoration-search approaches.
- **Capacitor support:** Evaluate configurations incorporating capacitor-based voltage support.
- **Thermal assessment:** Extract branch currents and compare them with supplied ampacity ratings when available.
- **Desktop interface:** Explore restoration scenarios and candidate results through a PySide6 GUI.
- **Automated testing:** Regression tests using pytest.

## Technology Stack

| Component | Technology |
|---|---|
| Programming language | Python |
| Graph modeling and algorithms | NetworkX |
| Power-flow simulation | OpenDSS / OpenDSSDirect.py |
| Desktop GUI | PySide6 |
| Testing | pytest |
| Results and experiment data | CSV |

## Project Architecture

GridResQ follows a modular design:

1. **Network modeling:** Constructs the distribution feeder and represents buses, branches, and switching connections as a graph.
2. **Fault and candidate generation:** Identifies candidate switching configurations subject to search constraints.
3. **Topology validation:** Checks whether candidate configurations satisfy the required graph constraints.
4. **Electrical evaluation:** Uses OpenDSS power flow to evaluate candidate configurations.
5. **Constraint assessment:** Examines voltage feasibility, graph/electrical consistency, and thermal status.
6. **Candidate comparison:** Compares restoration outcomes, including restored load and real-power losses.
7. **Visualization and reporting:** Presents candidate results in the desktop interface and stores benchmark outputs.

## Requirements

- Windows
- Python 3.12 or a compatible Python version
- Dependencies listed in `requirements.txt`

OpenDSSDirect.py is used for electrical power-flow evaluation. A compatible installation of the declared Python dependencies is required.

## Installation

Open PowerShell in the project directory.

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

If PowerShell blocks virtual-environment activation, use the Python executable directly:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

## Run the Desktop Application

Launch the PySide6 interface:

```powershell
python -m dashboard.desktop_app
```

The interface supports restoration-scenario evaluation and displays candidate results, including voltage measurements, real-power losses, restored load, thermal status, and rejection information where available.

## Run the Tests

Run the main regression suite:

```powershell
python -c "import opendssdirect; import pytest; raise SystemExit(pytest.main(['tests/', '-q']))"
```

**Latest recorded result:** 36 tests passed.

Rerun the suite after making code changes and before producing the final release.

## Benchmarking and Results

GridResQ includes scripts for evaluating the IEEE 33-bus feeder, restoration search, voltage support, and combined optimization.

The `results/` directory contains benchmark outputs and experiment data. The `artifacts/` directory is intended for final screenshots and validation evidence.

Reported simulation results should be interpreted in the context of the feeder model, candidate-generation settings, switching-operation limits, and electrical constraints used in each experiment.

## Electrical Constraints

The configured voltage limits are **0.95–1.05 per unit**.

Candidate evaluations consider power-flow convergence, voltage compliance, and graph/electrical consistency. A candidate that violates the configured voltage limits must not be described as voltage-feasible.

Lower real-power losses alone do not establish that a candidate is safe or suitable for operation.

## Thermal Assessment and Limitations

GridResQ includes branch-current extraction and thermal-limit checking. However, the current IEEE 33-bus configuration does not contain verified ampacity ratings for every branch.

Consequently, thermal compliance remains **`UNASSESSED`** until appropriate conductor ampacity ratings are supplied. The engine must not claim complete thermal verification in the absence of those ratings.

When verified ratings are available, the thermal assessment can compare calculated branch currents with the corresponding limits.

## Project Structure

```text
GridResQ/
├── dashboard/
│   ├── app.py
│   └── desktop_app.py
├── src/
│   ├── electrical_restoration.py
│   ├── ieee33_network.py
│   ├── ieee33_powerflow.py
│   ├── network.py
│   ├── restoration.py
│   ├── restoration_powerflow.py
│   ├── strategy_comparison.py
│   ├── thermal_analysis.py
│   └── thermal_limits.py
├── tests/
├── docs/
├── results/
├── artifacts/
├── benchmark_combined_optimization.py
├── benchmark_ieee33.py
├── requirements.txt
├── main.py
└── README.md
```

Additional benchmark scripts and archived diagnostic utilities may be present in the repository.

## Limitations

- GridResQ is a simulation-based research prototype, not a production distribution-management system.
- Results depend on the network model, switching constraints, search limits, and power-flow assumptions.
- Thermal safety cannot be confirmed without verified branch ampacity ratings.
- The simulation has not been validated on a physical distribution feeder.
- The software does not replace protection-system coordination, utility operating procedures, or engineering approval.

## Future Work

- Integrate verified conductor ampacity ratings.
- Expand multi-fault restoration validation.
- Evaluate additional fault scenarios and search budgets.
- Compare restoration strategies using repeatable benchmark experiments.
- Validate model assumptions and simulation results against authoritative feeder data.

## Safety Notice

GridResQ is intended for research, education, and simulation. Its outputs must not be used as direct switching instructions for a real distribution network without appropriate engineering validation and utility authorization.
