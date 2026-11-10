import argparse
from pathlib import Path

from .cohort import build


def main():
    parser = argparse.ArgumentParser(description="The First Four Cells")
    commands = parser.add_subparsers(dest="command", required=True)
    cohort = commands.add_parser("cohort", help="Build the analysis table and exclusion log")
    cohort.add_argument("--raw-dir", type=Path, default=Path("data/raw"))
    cohort.add_argument("--output-dir", type=Path, default=Path("data/processed"))
    experiment = commands.add_parser("evaluate", help="Run all timing baselines")
    experiment.add_argument("--cohort", type=Path, default=Path("data/processed/cohort.csv"))
    experiment.add_argument("--output", type=Path, default=Path("runs/baseline"))
    experiment.add_argument("--seed", type=int, default=42)
    experiment.add_argument("--groups", type=Path, help="CSV of verified embryo_id,group_id pairs")
    args = parser.parse_args()
    if args.command == "cohort":
        build(args.raw_dir, args.output_dir)
    else:
        from .evaluation import evaluate
        evaluate(args.cohort, args.output, args.seed, args.groups)
        print(f"Saved held-out predictions and metrics in {args.output}")


if __name__ == "__main__":
    main()
