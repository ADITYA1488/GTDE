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

| Runtime displayed | Approximately 1.26 seconds |



The displayed runtime and candidate count correspond to this demonstration run and are not general performance guarantees.



\## 4. Candidate Evaluation



The interface displays candidate switching configurations and their electrical results, including:



\- Closed tie switches and opened branches.

\- Restored load and restoration percentage.

\- Switching-operation count.

\- Power-flow convergence.

\- Voltage-feasibility status.

\- Minimum and maximum bus voltages.

\- Real-power losses.

\- Thermal status and rejection information where available.



The demonstration included candidates with acceptable voltage results and lower real-power losses than the baseline configuration. However, these results alone do not establish complete feasibility or operational safety.



In the displayed run, ten candidates were evaluated and zero met all current full-verification requirements.



\## 5. Thermal Assessment



GridResQ includes branch-current extraction and ampacity-checking logic. However, verified branch ampacity ratings have not been configured for every branch in the current benchmark.



Consequently, thermal compliance remains `UNASSESSED`. The application must not describe these candidates as thermally safe or fully verified.



This is a known limitation of the available benchmark data and does not mean that thermal-analysis code is absent.



\## 6. Automated Testing



The latest recorded regression run used:



```powershell

python -c "import opendssdirect; import pytest; raise SystemExit(pytest.main(\['tests/', '-q']))"

```



Recorded outcome:



\*\*36 tests passed.\*\*



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



The demonstration confirms that GridResQ can launch its desktop interface, evaluate a bounded set of restoration candidates, and display their electrical characteristics. The latest recorded regression suite passed 36 tests.



Further validation is needed to establish thermal compliance and broader performance across restoration scenarios. Results should be presented as simulation findings rather than proof of real-world operational safety.
