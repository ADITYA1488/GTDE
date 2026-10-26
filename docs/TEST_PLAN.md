\# GridResQ — Test Plan



\## 1. Purpose



This document describes the testing and validation approach for GridResQ, a graph-based distribution feeder restoration prototype using NetworkX, OpenDSS, and PySide6.



The objective is to validate the behavior of network modeling, restoration search, electrical evaluation, constraint handling, and supporting utilities.



\## 2. Test Environment



| Item | Configuration |

|---|---|

| Operating system | Windows |

| Language | Python |

| Graph library | NetworkX |

| Power-flow engine | OpenDSS via OpenDSSDirect.py |

| Desktop interface | PySide6 |

| Test framework | pytest |

| Benchmark network | IEEE 33-bus feeder |



Exact dependency versions should be taken from the project's installed environment and dependency configuration.



\## 3. Test Execution



Run the main regression suite from the project root:



```powershell

. .\.venv\Scripts\Activate.ps1
python -c "import opendssdirect; import pytest; raise SystemExit(pytest.main(['tests/', '-q']))"

```



The explicit OpenDSSDirect.py import is included because the Windows environment has previously required initialization before running the test suite.



\## 4. Recorded Test Result



The latest recorded regression run completed with:



\*\*62 passed in 3.72 seconds on 2026-10-25; runtime varies by environment.\*\*



This result applies to the test suite under `tests/` at the time of that run. It does not automatically establish that every standalone script, GUI workflow, or benchmark scenario has been tested.



\## 5. Test Categories



\### 5.1 Network Modeling



Verify that the feeder network is constructed correctly and that graph operations behave as expected.



Examples include:

\- Network structure and branch representation.

\- Connectivity and topology validation.

\- Switching-state handling.



\### 5.2 Restoration Search



Verify that restoration search generates candidate switching plans and respects configured search limits.



Examples include:

\- Candidate generation for fault scenarios.

\- Switching-operation constraints.

\- Search-budget handling.

\- Rejection of invalid parameter values.



\### 5.3 Fault Scenarios



Verify restoration behavior for supported fault scenarios, including multiple faulted branches where covered by the implemented tests.



\### 5.4 Electrical Evaluation



Verify that candidate configurations can be evaluated through the configured power-flow workflow.



Examples include:

\- Power-flow convergence handling.

\- Bus-voltage measurements.

\- Voltage-feasibility checks.

\- Electrical consistency checks.

\- Restored-load and loss results where available.



\### 5.5 Thermal Assessment



Verify the handling of branch currents and ampacity ratings.



Expected behavior includes:

\- Comparing current magnitudes against supplied ratings.

\- Identifying thermal violations when ratings are available.

\- Reporting `UNASSESSED` when required ratings are missing.



An unassessed thermal result must not be treated as a thermal pass.



\### 5.6 Desktop Application



Manually verify that:

\- The desktop application launches.

\- Fault and search settings can be configured.

\- Candidate results are displayed.

\- Voltage and loss metrics are visible.

\- Thermal status is represented accurately.



GUI behavior should be checked separately from the automated regression suite.



\## 6. Constraint Acceptance Criteria



| Check | Acceptance criterion |

|---|---|

| Power flow | Convergence status is reported accurately |

| Voltage | Configured voltage limits are applied correctly |

| Topology | Candidate topology passes the implemented checks |

| Search budget | Candidate evaluation respects configured limits |

| Thermal | Missing ratings produce `UNASSESSED` |

| Candidate verification | Unassessed thermal compliance does not qualify as full verification |

| Reporting | Results and rejection reasons are represented accurately where available |



Configured voltage limits are 0.95–1.05 p.u.



\## 7. Manual Validation Procedure



1\. Activate the project virtual environment.

2\. Run the regression suite.

3\. Launch the desktop interface using `python -m dashboard.desktop\_app`.

4\. Select a faulted branch and restoration strategy.

5\. Run candidate evaluation.

6\. Inspect convergence, voltage results, real-power losses, restored load, and thermal status.

7\. Confirm that candidates are not described as fully verified when thermal compliance is unassessed.

8\. Save the final screenshot and test output under `artifacts/`.



\## 8. Known Limitations



\- Passing regression tests does not establish physical feeder safety.

\- Thermal compliance remains unassessed until verified branch ampacity ratings are supplied.

\- Simulation results depend on the network model and evaluation settings.

\- Manual GUI checks and broader benchmark experiments are separate from the automated regression suite.



\## 9. Final Validation Record



Update this section after the final code changes.



\- Latest recorded automated tests: 62 passed in 3.72 seconds on 2026-10-25; runtime varies by environment.

\- Desktop application: previously launched successfully.

\- Benchmark model: IEEE 33-bus feeder.

\- Thermal compliance: `UNASSESSED` without verified branch ampacity ratings.

\- Physical feeder validation: not performed.



\## 10. Safety



GridResQ is a research and educational simulation prototype. Passing tests does not authorize its output to be used as real-world switching instructions. Independent engineering validation and utility authorization are required before operational use.
