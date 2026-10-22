\# GridResQ — Presentation Outline



\*\*Project title:\*\* GridResQ — Graph-Based Distribution Feeder Reconfiguration and Constraint-Aware Outage Restoration



\## Slide 1 — Title



\- GridResQ

\- Graph-Based Distribution Feeder Reconfiguration and Constraint-Aware Outage Restoration

\- Team members, department, institution, and supervisor



\## Slide 2 — Problem Statement



\- Branch faults can interrupt power delivery to distribution-network loads.

\- Restoration requires suitable switching configurations.

\- Candidate configurations must be evaluated for topology and electrical constraints.

\- GridResQ provides a software-based workflow for generating and comparing restoration candidates.



\## Slide 3 — Objectives



\- Model the feeder as a graph.

\- Generate candidate switching plans after faults.

\- Validate network topology.

\- Evaluate candidates using OpenDSS power flow.

\- Assess voltage constraints and power losses.

\- Compare baseline and adaptive search strategies.

\- Present results through a desktop application.



\## Slide 4 — System Architecture



Present the main components:



\- Network modeling

\- Restoration search

\- Topology validation

\- OpenDSS electrical evaluation

\- Voltage and thermal assessment

\- Candidate comparison

\- PySide6 desktop interface



Use the architecture diagram from `docs/ARCHITECTURE.md`.



\## Slide 5 — Technologies Used



\- Python

\- NetworkX

\- OpenDSS / OpenDSSDirect.py

\- PySide6

\- pytest

\- CSV-based benchmark results



Briefly explain the role of each technology.



\## Slide 6 — Restoration Workflow



Show the sequence:



1\. Select a faulted branch.

2\. Generate candidate switching plans.

3\. Validate topology.

4\. Evaluate candidates using power flow.

5\. Check voltage constraints and other feasibility conditions.

6\. Compare candidate results.

7\. Display the outcomes.



\## Slide 7 — Graph-Based Candidate Search



Explain:



\- Representation of buses and branches as a graph.

\- Candidate switching operations.

\- Switching-operation and candidate-search limits.

\- Topology validation before electrical evaluation.



Use a small illustrative network diagram if available.



\## Slide 8 — Electrical Evaluation



Explain how OpenDSS is used to evaluate:



\- Power-flow convergence.

\- Minimum and maximum bus voltage.

\- Restored load.

\- Real-power losses.



Configured voltage limits: 0.95–1.05 p.u.



\## Slide 9 — Adaptive Strategy and Optimization



\- Describe the baseline and adaptive restoration strategies implemented in the project.

\- Explain how candidate results are compared.

\- Show measured results from saved benchmark outputs.

\- Avoid claiming that one strategy is superior unless the experiment supports it.



\## Slide 10 — Desktop Application Demonstration



Insert a screenshot of the PySide6 interface.



Explain the visible controls and outputs:



\- Faulted branch and strategy selection.

\- Search limits.

\- Candidate configurations.

\- Voltage results and power losses.

\- Thermal status and rejection information.



\## Slide 11 — Experimental Results



Present the recorded IEEE 33-bus baseline:



\- 33 buses

\- 3,715 kW active load

\- 2,310 kvar reactive load

\- Minimum voltage: 0.916109 p.u.

\- Maximum voltage: 0.998397 p.u.

\- Real-power losses: 185.026371 kW

\- Reactive-power losses: 106.838697 kvar



State clearly that these are baseline values, and the minimum voltage is below the configured lower limit.



Add restoration and strategy-comparison results only after verifying the corresponding CSV data.



\## Slide 12 — Testing and Validation



\- Latest recorded regression result: 36 tests passed.

\- Describe the major test categories.

\- Show the test command or a screenshot of its output.

\- Explain that automated tests and GUI checks provide different forms of validation.



\## Slide 13 — Limitations



\- Thermal compliance is `UNASSESSED` without verified branch ampacity ratings.

\- Results are simulation-based.

\- The model has not been validated on a physical distribution feeder.

\- Search budgets limit the candidates evaluated.

\- Low losses alone do not establish safety.



\## Slide 14 — Conclusion and Future Work



Conclusion:

\- GridResQ combines graph-based candidate search with electrical evaluation.

\- The prototype provides a desktop workflow for analyzing restoration candidates.

\- The recorded regression suite passed 36 tests.



Future work:

\- Add verified ampacity ratings.

\- Expand fault-scenario evaluation.

\- Conduct repeatable strategy-comparison experiments.

\- Validate assumptions against authoritative feeder data.



\## Slide 15 — Questions



\- Thank the audience.

\- Invite questions about graph theory, restoration search, OpenDSS, electrical constraints, and project limitations.



\## Presentation Guidelines



\- Use actual screenshots and recorded experiment outputs.

\- Label baseline results separately from restoration results.

\- Do not claim thermal safety while ratings remain unverified.

\- Avoid claiming superiority of the adaptive strategy without supporting measurements.

\- Keep each slide focused on one principal idea.
