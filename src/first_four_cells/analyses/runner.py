"""Run selected analyses and publish a complete output directory."""

import hashlib
import json
from pathlib import Path
from tempfile import TemporaryDirectory

import numpy as np
import sklearn
from threadpoolctl import threadpool_limits

from ..evaluation import write_table
from . import (
    FAMILIES,
    forecasting,
    imaging,
    morphology,
    observation,
    phenotypes,
    sequences,
    trajectories,
)
from .events import inspect, stage_map


def run(args):
    raw_records, audit = inspect(args.data)
    maps = {i: stage_map(events) for i, events in raw_records.items()}
    families = (
        [family for family in FAMILIES if family not in ("grades", "images")]
        if args.family == "all"
        else [args.family]
    )
    if args.family == "all":
        if args.grades:
            families.append("grades")
        if args.manifest:
            families.append("images")
    if "grades" in families and not args.grades:
        raise ValueError("Use --grades PATH to provide the official morphology table.")
    if "images" in families and not args.manifest:
        raise ValueError(
            "Use --manifest PATH and --images DIR for the verified images."
        )
    destination = args.output
    if destination.exists():
        raise FileExistsError(f"Choose a fresh output directory: {destination}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory(dir=destination.parent) as tmp, threadpool_limits(limits=1):
        output = Path(tmp) / "results"
        output.mkdir()
        for family in families:
            if family == "audit":
                tables = {"recordings": audit}
            elif family == "trajectories":
                tables = trajectories.describe(raw_records)
            elif family == "benchmark":
                tables = forecasting.benchmark(args.cohort, args.seed, args.groups)
            elif family == "landmarks":
                tables = forecasting.landmarks(maps, args.seed, args.groups)
            elif family == "phenotypes":
                tables = phenotypes.describe(args.cohort, maps, args.seed)
            elif family == "sequences":
                tables = sequences.forecast(raw_records, maps, args.seed, args.groups)
            elif family == "observation":
                tables = observation.describe(
                    maps, raw_records, audit, args.seed, args.groups
                )
            elif family == "grades":
                tables = morphology.evaluate(args.grades, maps, args.seed, args.groups)
            else:
                tables = imaging.compare(
                    args.cohort, args.manifest, args.images, args.seed, args.groups
                )
            folder = output / family
            folder.mkdir()
            for name, rows in tables.items():
                if rows:
                    write_table(folder / (name + ".csv"), rows)
        sources = [args.cohort, args.grades, args.manifest, args.groups]
        metadata = dict(
            families=families,
            seed=args.seed,
            numpy=np.__version__,
            sklearn=sklearn.__version__,
            fold_unit="verified group" if args.groups else "embryo",
            hashes={
                str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in sources if p
            },
        )
        (output / "run.json").write_text(
            json.dumps(metadata, indent=2) + "\n", encoding="utf-8"
        )
        output.rename(destination)
    print(f"Saved {', '.join(families)} in {destination}")
