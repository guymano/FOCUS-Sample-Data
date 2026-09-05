"""CLI compatibility for the six direct-script entry points."""

import argparse
from pathlib import Path


def main(engine, argv=None, contract_csv=None):
    version = engine.adapter.version
    label = engine.profile.label
    parser = argparse.ArgumentParser(
        description=f"Generate synthetic {label} FOCUS {version} CSV data."
    )
    if contract_csv is not None:
        parser.add_argument(
            "--dataset",
            choices=("cost_and_usage", "contract_commitment"),
            default="cost_and_usage",
            help="FOCUS 1.3 dataset to emit (default: cost_and_usage)",
        )
    parser.add_argument(
        "--rows",
        type=int,
        default=1000,
        help="number of Cost/Usage rows" if contract_csv else "number of data rows",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=engine.adapter.default_seed,
        help="deterministic RNG seed",
    )
    parser.add_argument("--out", type=Path, default=None, help="output CSV path")
    parser.add_argument(
        "--include-credits",
        action="store_true",
        help="emit some Credit rows with negative BilledCost (excluded from the default fixture)",
    )
    args = parser.parse_args(argv)
    dataset = args.dataset if contract_csv else "cost_and_usage"
    if dataset == "contract_commitment":
        payload = contract_csv(args.rows, args.seed)
        out = args.out or Path(
            f"FOCUS-{version}/focus_sample_contractcommitment_{engine.profile.key}.csv"
        )
        columns = engine.adapter.contract_columns
    else:
        payload = engine.generate_csv_bytes(
            args.rows, args.seed, include_credits=args.include_credits
        )
        out = args.out or Path(
            f"FOCUS-{version}/focus_sample_costandusage_{engine.profile.key}_1000.csv"
        )
        columns = engine.adapter.columns
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(payload)
    prefix = "" if label == "AWS" else label + " "
    if contract_csv:
        print(
            f"Wrote {dataset} ({len(columns)} {prefix}FOCUS {version} columns) -> {out}"
        )
    else:
        print(
            f"Wrote {args.rows} rows x {len(columns)} {prefix}FOCUS {version} columns -> {out}"
        )
    return 0
