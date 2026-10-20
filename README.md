# GraD — Graph-Theory Driven Feeder Restoration Engine

A software prototype for distribution feeder reconfiguration and
outage restoration using graph theory and optional OpenDSS simulation.

## Features
- Synthetic six-bus feeder model
- Branch fault simulation
- Bounded switching-plan search
- Radial topology validation
- Restored-load calculations
- Optional OpenDSS electrical evaluation
- CLI and Streamlit dashboard
- Automated tests with pytest

## Setup

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python main.py
python -m pytest -q