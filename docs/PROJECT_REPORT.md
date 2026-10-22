\# GridResQ: Graph-Based Distribution Feeder Reconfiguration and Constraint-Aware Outage Restoration



\## Abstract



GridResQ is a software-based prototype for analyzing distribution feeder reconfiguration and outage restoration following branch faults. The system combines graph-theoretic switching-plan generation, topology validation, and electrical power-flow evaluation using OpenDSS. It evaluates candidate restoration configurations based on network connectivity, voltage constraints, restored load, and real-power losses. Baseline and adaptive search strategies support candidate comparison through a PySide6 desktop interface.



The prototype is evaluated using an IEEE 33-bus distribution feeder model. The regression suite contains 36 passing tests in the latest recorded validation. Thermal analysis is implemented, but thermal compliance remains unassessed until verified branch ampacity ratings are provided. The project demonstrates a simulation-based workflow for candidate restoration analysis rather than a production-ready utility control system.



\## 1. Introduction



Electrical distribution networks may experience branch faults that interrupt power delivery to downstream loads. Following fault isolation, operators can restore service to some affected loads by changing network switch configurations while maintaining acceptable electrical operating conditions.



Feeder restoration is challenging because a switching configuration that improves connectivity may also produce unacceptable bus voltages, violate network constraints, or increase power losses. Graph-based search can generate candidate configurations, while electrical simulation can evaluate their operating characteristics.



GridResQ combines these approaches in a modular software prototype. It generates candidate switching plans, validates network topology, evaluates electrical behavior, and presents the resulting comparisons through a desktop application.



\## 2. Problem Statement



Develop a software engine that evaluates candidate distribution feeder restoration configurations following branch faults.



The engine must consider:

\- Faulted branches and candidate switching operations.

\- Network connectivity and topology constraints.

\- Power-flow convergence.

\- Bus-voltage operating limits.

\- Restored load and real-power losses.

\- Thermal-limit assessment when verified branch ampacity ratings are available.



The goal is to identify and compare candidate configurations that satisfy the implemented constraints, while clearly distinguishing fully verified candidates from candidates whose thermal status remains unassessed.



\## 3. Objectives



The main objectives are:



1\. Represent a distribution feeder as a graph.

2\. Generate candidate switching plans under configurable search limits.

3\. Validate candidate network topology.

4\. Evaluate candidate configurations through OpenDSS power flow.

5\. Assess bus voltages against configured operating limits.

6\. Compare restoration outcomes using restored load and real-power losses.

7\. Compare baseline and adaptive search strategies.

8\. Provide an interactive desktop interface for inspecting candidate results.

9\. Validate implementation behavior through automated tests.

10\. Report model limitations and unverified constraints explicitly.



\## 4. Scope



GridResQ is a software simulation project. It does not require a physical distribution feeder or embedded hardware.



The current evaluation uses an IEEE 33-bus feeder model and OpenDSS-based power-flow analysis. The project includes graph-based candidate search, electrical constraint checking, capacitor-support evaluation, a desktop dashboard, and benchmark scripts.



Thermal analysis is included, but verified conductor ampacity ratings are not currently configured for every branch. Therefore, the prototype cannot claim complete thermal verification.



\## 5. System Architecture



The system consists of the following logical components.



\### 5.1 Network Modeling



The network module constructs the feeder representation, including buses, branches, and switching connections. Graph structures support connectivity analysis and candidate topology validation.



\### 5.2 Fault and Candidate Generation



The restoration search generates candidate switching plans based on the fault scenario, maximum switching operations, and candidate-search limits.



\### 5.3 Topology Validation



Candidate configurations are checked against the implemented graph constraints. Graph and electrical representations are compared to identify inconsistencies.



\### 5.4 Electrical Evaluation



OpenDSSDirect.py provides access to OpenDSS power-flow simulation. Candidate configurations are evaluated for convergence, bus voltages, restored load, and real-power losses.



\### 5.5 Constraint Assessment



The evaluation workflow considers voltage compliance, topology/electrical consistency, and thermal status. A candidate with unassessed thermal compliance is not treated as fully verified.



\### 5.6 Strategy Comparison



Baseline and adaptive search strategies can be evaluated under configured search constraints. Candidate results can be compared using electrical performance metrics.



\### 5.7 Desktop Interface



The PySide6 application allows users to select a faulted branch, choose a search strategy, configure operation and evaluation limits, and inspect candidate results.



\## 6. Methodology



The restoration-analysis workflow is:



1\. Construct the feeder model.

2\. Select the fault scenario.

3\. Generate candidate switching plans.

4\. Validate candidate topology.

5\. Evaluate candidate configurations using power flow.

6\. Check convergence and voltage constraints.

7\. Extract branch-current information for thermal assessment.

8\. Compare restored load and real-power losses.

9\. Rank and display candidate configurations according to the implemented selection rules.

10\. Report constraint failures and unassessed conditions.



A low-loss candidate is not automatically considered safe. Candidate selection must respect the implemented feasibility requirements.



\## 7. Electrical Constraints and Metrics



\### 7.1 Voltage Limits



The configured bus-voltage limits are:



\\\[

0.95 \\leq V\_i \\leq 1.05 \\text{ p.u.}

\\]



where \\(V\_i\\) denotes the per-unit voltage magnitude at bus \\(i\\).



A candidate violating these limits must not be classified as voltage-feasible.



\### 7.2 Restored Load



Restored load measures the demand supplied by the evaluated configuration, according to the network model and restoration-evaluation logic.



\### 7.3 Real-Power Losses



Real-power losses, expressed in kilowatts, provide a measure for comparing candidate operating configurations. Lower losses are beneficial only when the relevant feasibility constraints are also satisfied.



\### 7.4 Thermal Assessment



Branch-current magnitudes are extracted from electrical evaluation and can be compared against branch ampacity ratings.



Because verified ratings are not currently configured for every branch, the reported thermal status remains `UNASSESSED`. This prevents the system from claiming thermal safety without supporting data.



\## 8. Implementation and Technology



The prototype uses:



\- Python for application logic and restoration analysis.

\- NetworkX for graph modeling and graph algorithms.

\- OpenDSS and OpenDSSDirect.py for electrical power-flow evaluation.

\- PySide6 for the desktop interface.

\- pytest for automated regression testing.

\- CSV files for benchmark and experiment results.



The repository separates network modeling, restoration search, electrical evaluation, thermal analysis, desktop presentation, and test code into distinct modules.



\## 9. Experimental Evaluation



The project includes an IEEE 33-bus benchmark and scripts for restoration search, voltage support, and combined optimization.



The baseline power-flow validation previously recorded the following results:



| Metric | Recorded value |

|---|---:|

| Buses | 33 |

| Configured active load | 3,715 kW |

| Configured reactive load | 2,310 kvar |

| Minimum bus voltage | 0.916109 p.u. |

| Maximum bus voltage | 0.998397 p.u. |

| Real-power losses | 185.026371 kW |

| Reactive-power losses | 106.838697 kvar |



These values describe the recorded baseline configuration, not a restored configuration. The minimum baseline voltage is below the configured 0.95 p.u. lower limit.



The desktop application has also demonstrated candidate evaluation for a selected branch-fault scenario. In the recorded screenshot, ten candidates were evaluated, but zero satisfied all current full-verification requirements because thermal compliance remained unassessed.



Candidate-level results and benchmark CSV files should be consulted when reporting restoration performance. Do not present a candidate as fully feasible solely because it converges or has acceptable voltage.



\## 10. Testing and Validation



The latest recorded regression run used:



```powershell

python -c "import opendssdirect; import pytest; raise SystemExit(pytest.main(\['tests/', '-q']))"

```



Recorded result:



\*\*36 tests passed.\*\*



The regression suite covers the test cases present under `tests/` at the time of that run. The test result should be refreshed after code changes and before final submission.



The desktop application has also been launched successfully and displayed restoration candidate results.



\## 11. Limitations



The current prototype has several limitations:



1\. The evaluation is simulation-based and has not been validated on a physical distribution feeder.

2\. Thermal compliance cannot be confirmed without verified branch ampacity ratings.

3\. Results depend on the feeder model, electrical assumptions, search limits, and candidate-generation logic.

4\. A finite search budget may prevent the engine from evaluating every possible switching configuration.

5\. Results from the IEEE 33-bus model do not establish performance for every real-world distribution network.

6\. Candidate rankings must not be interpreted as operational switching instructions.



\## 12. Future Work



Potential extensions include:



\- Incorporating documented conductor ampacity ratings for every evaluated branch.

\- Expanding multi-fault and switching-scenario validation.

\- Evaluating more search budgets and restoration scenarios.

\- Performing repeatable statistical comparisons of baseline and adaptive strategies.

\- Comparing simulation assumptions with authoritative feeder data.

\- Improving result export, reproducibility, and experiment reporting.

\- Validating the model against utility-approved engineering cases.



\## 13. Conclusion



GridResQ demonstrates a modular software workflow for graph-based distribution feeder restoration analysis. It combines candidate switching-plan generation, topology validation, OpenDSS power-flow evaluation, voltage constraint checking, and candidate comparison in a desktop application.



The latest recorded regression suite passed 36 tests. However, thermal compliance remains unassessed because verified branch ampacity ratings have not been supplied for every branch. The prototype is therefore suitable for research and educational simulation, with further validation required before any real-world operational use.



\## Safety Notice



GridResQ is a research and educational simulation prototype. Its results must not be used as direct switching instructions for a real distribution network without independent engineering validation and appropriate utility authorization.
