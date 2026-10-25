\# GridResQ — Demonstration Results



\## 1. Overview



This document records the available validation and demonstration results for GridResQ, a graph-based distribution feeder reconfiguration and outage restoration prototype.



The project uses an IEEE 33-bus distribution feeder model, graph-based restoration search, OpenDSS power-flow evaluation, and a PySide6 desktop interface.



\## 2. Baseline IEEE 33-Bus Evaluation



The following baseline values were recorded during power-flow validation.



| Metric | Recorded value |

|---|---:|

| Number of buses | 33 |

| Configured active load | 3,715 kW |

| Configured reactive load | 2,310 kvar |

| Minimum bus voltage | 0.916109 p.u. |

| Maximum bus voltage | 0.998397 p.u. |

| Real-power losses | 185.026371 kW |

| Reactive-power losses | 106.838697 kvar |



The recorded minimum voltage is below the configured lower limit of 0.95 p.u. This baseline result therefore does not satisfy the configured voltage constraint.



These figures describe the baseline configuration and must not be interpreted as the performance of a restored configuration.



\## 3. Desktop Demonstration



The PySide6 desktop application was launched successfully and used to evaluate a restoration scenario for faulted branch `L10`.



Recorded interface settings and outcomes:



| Item | Recorded value |

|---|---|

| Faulted branch | L10 |

| Search strategy | Adaptive |

| Maximum switching operations | 3 |

| OpenDSS evaluation budget | 10 |

| Candidates evaluated | 10 |

| Fully verified candidates | 0 |

| Capacitor support | Enabled: 900 kvar at bus 33 |

| Runtime displayed | Approximately 1.26 seconds |



The displayed runtime and candidate count correspond to this demonstration run and are not general performance guarantees.



\## 4. Candidate Evaluation



The interface displays candidate switching configurations and their electrical results, including:



\- Closed tie switches and opened branches.

\- Graph-connected load and restoration percentage.

\- Switching-operation count.

\- Power-flow convergence.

\- Voltage-feasibility status.

\- Minimum and maximum bus voltages.

\- Real-power losses.

\- Thermal status and rejection information where available.



The demonstration used the desktop application's default capacitor support: 900 kvar at bus 33. It included candidates with acceptable voltage results and lower real-power losses than the no-capacitor baseline configuration. These results alone do not establish complete feasibility or operational safety.



In the displayed run, ten candidates were evaluated and zero met all current full-verification requirements.



\## 5. Thermal Assessment



GridResQ includes branch-current extraction and ampacity-checking logic. However, verified branch ampacity ratings have not been configured for every branch in the current benchmark.



Consequently, thermal compliance remains `UNASSESSED`. The application must not describe these candidates as thermally safe or fully verified.



This is a known limitation of the available benchmark data and does not mean that thermal-analysis code is absent.

\## No-Capacitor Voltage Diagnostic and Recovery-Path Comparison

A separate controlled diagnostic used the IEEE 33-bus feeder without capacitor support, 3 switching operations, an evaluation budget of 10, and voltage limits of 0.95–1.05 p.u. The baseline minimum was **0.916109 p.u. at bus 18**, already below the lower limit. Across faults L04, L05, L10, and L20, 10 candidates per fault were evaluated. All 40 converged and were graph/electrically consistent, but all 40 failed voltage compliance. Their reported **3715 kW** is graph-connected load, not voltage-compliant served load.

| Fault | Evaluated | Converged and graph/electrically consistent | Voltage-compliant | Candidate minimum-voltage range (p.u.) | Candidate maximum-voltage range (p.u.) |
|---|---:|---:|---:|---:|---:|
| L04 | 10 | 10 | 0 | 0.816999–0.927513 | 0.998370–0.998488 |
| L05 | 10 | 10 | 0 | 0.820407–0.927511 | 0.998371–0.998484 |
| L10 | 10 | 10 | 0 | 0.881945–0.936854 | 0.998376–0.998413 |
| L20 | 10 | 10 | 0 | 0.908095–0.926451 | 0.998377–0.998401 |

The separate `benchmark_ieee33.py` experiment uses 900 kvar capacitor support at bus 33; its results must be interpreted separately. In the recovery-path comparison, the priority changed some retained plans but did not change evaluated outcomes. No improvement in evaluated electrical results was demonstrated. Thermal compliance remained `UNASSESSED` in both experimental configurations because verified ampacity ratings were unavailable.

The separate capacitor-supported benchmark evaluated 10 candidates per fault with 3 switching operations and a 10-candidate electrical budget. Baseline and adaptive produced the same electrically feasible counts:

| Fault | Electrically feasible candidates | Lowest-loss result, if any | Minimum voltage |
|---|---:|---:|---:|
| L05 | 0 | — | — |
| L10 | 4 | 113.747 kW | 0.9513 p.u. |
| L15 | 0 | — | — |
| L20 | 0 | — | — |
| L25 | 2 | 121.586 kW | 0.9507 p.u. |
| L30 | 4 | 156.509 kW | 0.9514 p.u. |

These counts mean electrically feasible only. All reported thermal statuses were `UNASSESSED`, so the fully verified count was zero.



\## 6. Automated Testing



The latest recorded regression run used:



```powershell

. .\.venv\Scripts\Activate.ps1
python -c "import opendssdirect; import pytest; raise SystemExit(pytest.main(['tests/', '-q']))"

```



Recorded outcome:



\*\*62 tests passed in 3.72 seconds on 2026-10-25; runtime varies by environment.\*\*



The test suite should be rerun after subsequent source-code changes and before the final project submission.



\## 7. Evidence and Reproducibility



Relevant project evidence is maintained in:



\- `results/` — benchmark outputs, CSV files, and plots.

\- `artifacts/` — intended location for the final GUI screenshot and test-result evidence.

\- `tests/` — automated regression tests.

\- Root-level benchmark scripts — repeatable restoration and optimization experiments.



The final submission should include the current GUI screenshot and the latest test output. Any reported benchmark value should be traceable to the corresponding saved results or experiment.



\## 8. Limitations



\- The project is a simulation-based prototype.

\- The baseline minimum voltage violates the configured lower voltage limit.

\- Thermal compliance remains unassessed without verified branch ampacity ratings.

\- Candidate results depend on the network model, search limits, and evaluation configuration.

\- The simulation has not been validated on a physical distribution feeder.

\- The application is not a replacement for utility operating procedures or engineering approval.



\## 9. Conclusion



The demonstration confirms that GridResQ can launch its desktop interface, evaluate a bounded set of restoration candidates, and display their electrical characteristics. The latest documented regression suite run passed 62 tests in 3.72 seconds on 2026-10-25; runtime varies by environment.



Further validation is needed to establish thermal compliance and broader performance across restoration scenarios. Results should be presented as simulation findings rather than proof of real-world operational safety.
