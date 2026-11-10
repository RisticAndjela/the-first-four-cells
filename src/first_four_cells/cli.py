import argparse
from pathlib import Path

from .cohort import build


def main():
    parser = argparse.ArgumentParser(description="The First Four Cells")
    commands = parser.add_subparsers(dest="command", required=True)
    cohort = commands.add_parser("cohort", help="Build the analysis table and exclusion log")
    cohort.add_argument("--raw-dir", type=Path, default=Path("data"))
    cohort.add_argument("--output-dir", type=Path, default=Path("data/processed"))
    experiment = commands.add_parser("evaluate", help="Run all timing baselines")
    experiment.add_argument("--cohort", type=Path, default=Path("data/processed/cohort.csv"))
    experiment.add_argument("--output", type=Path, default=Path("runs/baseline"))
    experiment.add_argument("--seed", type=int, default=42)
    experiment.add_argument("--groups", type=Path, help="CSV of verified embryo_id,group_id pairs")
    manifest = commands.add_parser("image-manifest", help="Verify first four-cell images")
    manifest.add_argument("--annotations", type=Path, help="Override the automatically detected annotations folder")
    manifest.add_argument("--images", type=Path, default=Path("data/raw/embryo_dataset"))
    manifest.add_argument("--cohort", type=Path, default=Path("data/processed/cohort.csv"))
    manifest.add_argument("--output", type=Path, default=Path("data/processed/t4_image_manifest.csv"))
    view = commands.add_parser("visualize", help="Create an interactive offline HTML comparison")
    view.add_argument("--cohort", type=Path, default=Path("data/processed/cohort.csv"))
    view.add_argument("--predictions", type=Path, default=Path("results/reference/predictions.csv"))
    view.add_argument("--manifest", type=Path, default=Path("data/processed/t4_image_manifest.csv"))
    view.add_argument("--images", type=Path, default=Path("data/raw/embryo_dataset"))
    view.add_argument("--output", type=Path, default=Path("reports/embryo-explorer.html"))
    from .analyses import FAMILIES
    analysis = commands.add_parser("research", help="Run the extended research packages")
    analysis.add_argument("family", choices=("all", *FAMILIES))
    analysis.add_argument("--data", type=Path, default=Path("data"))
    analysis.add_argument("--cohort", type=Path, default=Path("data/processed/cohort.csv"))
    analysis.add_argument("--output", type=Path, default=Path("runs/research"))
    analysis.add_argument("--seed", type=int, default=42)
    analysis.add_argument("--groups", type=Path)
    analysis.add_argument("--grades", type=Path)
    analysis.add_argument("--manifest", type=Path)
    analysis.add_argument("--images", type=Path, default=Path("data/raw/embryo_dataset"))
    args = parser.parse_args()
    if args.command == "research":
        from .analyses.runner import run
        run(args)
        return
    if args.command == "cohort":
        build(args.raw_dir, args.output_dir)
    elif args.command == "visualize":
        from .visualization import report
        report(args.cohort, args.predictions, args.manifest, args.images, args.output)
        print(f"Open {args.output.resolve()} in your browser.")
    elif args.command == "image-manifest":
        from .images import build_manifest
        try:
            from .layout import source_folder
            annotations = args.annotations or source_folder(Path("data"), "embryo_dataset_annotations", "_phases.csv")
            usable, total = build_manifest(args.cohort, annotations, args.images, args.output)
        except (ValueError, OSError) as error:
            parser.exit(1, f"{error}\n")
        print(f"Decoded {usable}/{total} four-cell images. See {args.output}")
        if not usable:
            parser.exit(1, "Check the central-plane directory and the manifest status column.\n")
    else:
        from .evaluation import evaluate
        evaluate(args.cohort, args.output, args.seed, args.groups)
        print(f"Saved held-out predictions and metrics in {args.output}")


if __name__ == "__main__":
    main()
