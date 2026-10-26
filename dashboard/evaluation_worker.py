"""Subprocess entry point for the existing OpenDSS-backed dashboard calls."""

from __future__ import annotations

from contextlib import redirect_stdout
from dataclasses import asdict
import io
import json
import sys


def main():
    request = json.load(sys.stdin)
    settings = request["settings"]
    diagnostics = io.StringIO()
    with redirect_stdout(diagnostics):
        if request["mode"] == "evaluate":
            from src.ieee33_network import build_ieee33_network
            from src.restoration_powerflow import evaluate_restoration_plans

            results = evaluate_restoration_plans(
                build_ieee33_network(), **settings
            )
            payload = []
            for result in results:
                row = asdict(result)
                row["plan"] = asdict(result.plan)
                payload.append(row)
        elif request["mode"] == "compare":
            from src.ieee33_network import build_ieee33_network
            from src.strategy_comparison import compare_strategies

            payload = compare_strategies(build_ieee33_network(), **settings)
        else:
            raise ValueError(f"Unknown worker mode {request['mode']!r}")
    json.dump(payload, sys.stdout, allow_nan=False)


if __name__ == "__main__":
    main()
