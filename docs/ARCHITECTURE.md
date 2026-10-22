\# GridResQ — System Architecture



\## 1. Overview



GridResQ is a modular software prototype for graph-based distribution feeder reconfiguration and outage restoration. It combines graph-based candidate generation, topology validation, OpenDSS power-flow evaluation, constraint checking, and desktop visualization.



\## 2. Architecture Layers



\### Layer 1: Network Model



\*\*Primary modules:\*\* `src/ieee33\_network.py`, `src/ieee33\_electrical\_data.py`, `src/network.py`



Responsibilities:

\- Construct the IEEE 33-bus feeder representation.

\- Represent buses, branches, and switching connections.

\- Provide the network structure used by restoration search.

\- Support graph connectivity and topology checks.



\### Layer 2: Restoration Search



\*\*Primary module:\*\* `src/restoration.py`



Responsibilities:

\- Generate candidate switching plans for a specified fault scenario.

\- Apply limits on switching operations and candidate count.

\- Produce configurations for subsequent topology and electrical evaluation.



\### Layer 3: Electrical Evaluation



\*\*Primary modules:\*\* `src/ieee33\_powerflow.py`, `src/powerflow.py`, `src/electrical\_restoration.py`



Responsibilities:

\- Evaluate candidate configurations through OpenDSS where configured.

\- Retrieve power-flow convergence information.

\- Calculate or extract bus-voltage and real-power-loss results.

\- Support electrical evaluation of restoration plans.



\### Layer 4: Restoration Evaluation and Strategy Selection



\*\*Primary modules:\*\* `src/restoration\_powerflow.py`, `src/strategy\_comparison.py`



Responsibilities:

\- Coordinate candidate restoration evaluation.

\- Check voltage feasibility and graph/electrical consistency.

\- Compare baseline and adaptive restoration strategies.

\- Rank candidates according to the implemented evaluation and selection rules.



\### Layer 5: Thermal Assessment



\*\*Primary modules:\*\* `src/thermal\_analysis.py`, `src/thermal\_limits.py`



Responsibilities:

\- Extract branch-current magnitudes.

\- Compare currents with ampacity ratings when ratings are provided.

\- Report thermal status, including `PASS`, `VIOLATION`, or `UNASSESSED`, as supported by the implementation.



Thermal status remains `UNASSESSED` when verified ampacity ratings are unavailable.



\### Layer 6: User Interface



\*\*Primary module:\*\* `dashboard/desktop\_app.py`



Responsibilities:

\- Allow users to configure the faulted branch and search settings.

\- Start restoration evaluation.

\- Display candidate metrics, voltage results, and power losses.

\- Show thermal status and candidate rejection information where available.



The repository also contains `dashboard/app.py`, a separate dashboard implementation.



\### Layer 7: Testing and Experiments



\*\*Primary locations:\*\* `tests/`, root-level test scripts, benchmark scripts, `results/`



Responsibilities:

\- Test network and restoration behavior.

\- Validate electrical evaluation and constraint handling.

\- Run benchmark experiments.

\- Store experiment outputs for comparison and reporting.



\## 3. High-Level Execution Flow



1\. The user selects a faulted branch and configures the search parameters.

2\. The application constructs or loads the feeder network.

3\. The restoration engine generates candidate switching plans.

4\. Candidate topology is checked against the implemented graph constraints.

5\. Eligible candidates undergo electrical evaluation.

6\. Voltage, convergence, topology consistency, and thermal status are assessed.

7\. Candidate results are ranked and presented in the interface.

8\. Benchmark or experiment scripts can store results for further analysis.



\## 4. Architecture Diagram



```text

User

&#x20;|

&#x20;v

PySide6 Desktop Interface

&#x20;|

&#x20;v

Restoration Evaluation Coordinator

&#x20;|

&#x20;+---------------------------+

&#x20;|                           |

&#x20;v                           v

Network Model          Candidate Search

&#x20;|                           |

&#x20;+-------------+-------------+

&#x20;              |

&#x20;              v

&#x20;      Topology Validation

&#x20;              |

&#x20;              v

&#x20;      OpenDSS Power Flow

&#x20;              |

&#x20;              v

&#x20;      Constraint Assessment

&#x20;       |       |       |

&#x20;       v       v       v

&#x20;     Voltage  Graph   Thermal

&#x20;     Checks   Checks  Assessment

&#x20;              |

&#x20;              v

&#x20;      Candidate Comparison

&#x20;              |

&#x20;              v

&#x20;       Results and Metrics

```



\## 5. Feasibility and Safety



GridResQ distinguishes promising electrical results from fully verified candidates.



A candidate's low real-power losses do not establish feasibility by themselves. The implemented evaluation also considers convergence, voltage constraints, and graph/electrical consistency.



Thermal compliance cannot be confirmed when verified ampacity ratings are missing. Such candidates must not be represented as fully verified or thermally safe.



\## 6. Design Limitations



\- The application is a simulation-based research prototype.

\- Search results depend on candidate limits and evaluation settings.

\- Electrical results depend on the feeder model and OpenDSS configuration.

\- Thermal safety requires suitable branch ampacity data.

\- The architecture does not replace utility protection, switching, or operational approval processes.
