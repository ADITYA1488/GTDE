import pandas as pd
from pathlib import Path

INPUT = Path("results/restoration_experiments.csv")
OUTPUT = Path("results/experiment_summary.csv")


def main():
    if not INPUT.exists():
        raise FileNotFoundError(
            f"Missing {INPUT}. Run python run_experiments.py first."
        )

    df = pd.read_csv(INPUT)

    if df.empty:
        raise ValueError("Experiment CSV contains no candidates.")

    df["feasible"] = (
        df["feasible"].astype(str).str.strip().str.lower()
        .map({"true": True, "false": False})
        .fillna(False)
    )

    feasible = df[df["feasible"]].copy()

    if feasible.empty:
        print("No electrically feasible candidates were recorded.")
        return

    # Best loss among feasible candidates for each fault.
    lowest_loss = (
        feasible.sort_values(
            ["fault", "real_losses_kw", "switching_operations"]
        )
        .groupby("fault", as_index=False)
        .first()
    )

    # Fewest operations among feasible candidates that restore all load.
    full_restoration = feasible[
        feasible["restoration_pct"] >= 99.999
    ]

    fewest_operations = (
        full_restoration.sort_values(
            ["fault", "switching_operations", "real_losses_kw"]
        )
        .groupby("fault", as_index=False)
        .first()
    )

    lowest_loss["selection_method"] = "Lowest real losses"
    fewest_operations["selection_method"] = (
        "Fewest operations with full restoration"
    )

    summary = pd.concat(
        [lowest_loss, fewest_operations],
        ignore_index=True,
    ).drop_duplicates(
        subset=[
            "fault", "close_ties", "open_branches",
            "selection_method",
        ]
    )

    summary.to_csv(OUTPUT, index=False)

    print(f"Candidates in CSV: {len(df)}")
    print(f"Feasible candidates: {len(feasible)}")
    print(f"Fault scenarios: {feasible['fault'].nunique()}")
    print(f"Summary saved: {OUTPUT}")

    columns = [
        "fault", "selection_method", "close_ties",
        "open_branches", "restoration_pct",
        "switching_operations", "real_losses_kw",
    ]

    print("\nSummary:")
    print(summary[columns].to_string(index=False))


if __name__ == "__main__":
    main()