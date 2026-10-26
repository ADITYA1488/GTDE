"""Run OpenDSS-backed dashboard evaluations outside Streamlit's script thread.

The installed OpenDSS native backend is not reliable when invoked from the
Streamlit script thread on Windows. This module invokes the existing project
evaluator in a short-lived Python process; it does not implement search or
power-flow logic itself.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace


_PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _jsonable(value):
    if isinstance(value, set):
        return sorted(value)
    if isinstance(value, tuple):
        return [_jsonable(item) for item in value]
    if isinstance(value, list):
        return [_jsonable(item) for item in value]
    if isinstance(value, dict):
        return {key: _jsonable(item) for key, item in value.items()}
    return value


def _invoke(payload, timeout_seconds=300):
    completed = subprocess.run(
        [sys.executable, "-m", "dashboard.evaluation_worker"],
        input=json.dumps(_jsonable(payload)),
        capture_output=True,
        text=True,
        cwd=_PROJECT_ROOT,
        env=os.environ.copy(),
        timeout=timeout_seconds,
        check=False,
    )
    if completed.returncode:
        detail = completed.stderr.strip() or completed.stdout.strip()
        raise RuntimeError(
            f"OpenDSS evaluation worker exited with code {completed.returncode}. "
            f"{detail[-2000:]}"
        )
    try:
        return json.loads(completed.stdout)
    except json.JSONDecodeError as exc:
        raise RuntimeError("OpenDSS evaluation worker returned invalid output.") from exc


def evaluate_restoration(**settings):
    """Call the existing restoration evaluator and restore result objects."""
    payload = _invoke({"mode": "evaluate", "settings": settings})
    results = []
    for row in payload:
        plan = SimpleNamespace(**row.pop("plan"))
        results.append(SimpleNamespace(plan=plan, **row))
    return results


def compare_restoration_strategies(**settings):
    """Run the existing strategy comparison in the isolated worker process."""
    return _invoke({"mode": "compare", "settings": settings})
