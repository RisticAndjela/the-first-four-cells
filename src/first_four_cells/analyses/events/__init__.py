"""Read the complete event ledger and audit the frame clocks."""

import csv
from collections import Counter
from dataclasses import dataclass
from math import isfinite
from statistics import median

from ...layout import source_folder

STAGES = (
    "tPB2",
    "tPNa",
    "tPNf",
    "t2",
    "t3",
    "t4",
    "t5",
    "t6",
    "t7",
    "t8",
    "t9+",
    "tM",
    "tSB",
    "tB",
    "tEB",
    "tHB",
)


@dataclass(frozen=True)
class Event:
    stage: str
    first: int
    last: int
    start_h: float | None
    last_h: float | None


def inspect(root):
    phases = source_folder(root, "embryo_dataset_annotations", "_phases.csv")
    clocks = source_folder(root, "embryo_dataset_time_elapsed", "_timeElapsed.csv")
    records, audit = {}, []
    for path in sorted(phases.glob("*_phases.csv")):
        embryo = path.name.removesuffix("_phases.csv")
        times = {}
        duplicates = conflicts = 0
        clock_file = clocks / f"{embryo}_timeElapsed.csv"
        if clock_file.exists():
            with clock_file.open(newline="") as handle:
                for row in csv.DictReader(handle):
                    frame, hour = int(row["frame_index"]), float(row["time"])
                    if frame in times:
                        duplicates += 1
                        if times[frame] != hour:
                            conflicts += 1
                            times[frame] = None
                    else:
                        times[frame] = hour if isfinite(hour) else None
        ordered = sorted((f, t) for f, t in times.items() if t is not None)
        steps = [b[1] - a[1] for a, b in zip(ordered, ordered[1:])]
        positives = [s for s in steps if s > 0]
        with path.open(newline="") as handle:
            events = [
                Event(stage, int(a), int(b), times.get(int(a)), times.get(int(b)))
                for stage, a, b in csv.reader(line for line in handle if line.strip())
            ]
        if any(e.stage not in STAGES or e.first > e.last for e in events):
            raise ValueError(f"Unknown stage or invalid frame interval in {path}")
        records[embryo] = sorted(events, key=lambda e: e.first)
        audit.append(
            dict(
                embryo_id=embryo,
                frames=len(times),
                annotated=len(events),
                orphan_starts=sum(e.start_h is None for e in events),
                orphan_ends=sum(e.last_h is None for e in events),
                repeated_stage=len(events) - len(set(e.stage for e in events)),
                duplicate_frames=duplicates,
                conflicting_frames=conflicts,
                nonincreasing_steps=sum(s <= 0 for s in steps),
                median_positive_step_h=median(positives) if positives else None,
                largest_step_h=max(steps, default=None),
                last_recorded_h=ordered[-1][1] if ordered else None,
            )
        )
    expected = {
        p.name.removesuffix("_timeElapsed.csv")
        for p in clocks.glob("*_timeElapsed.csv")
    }
    if expected - records.keys():
        raise ValueError(
            f"Timestamp files without annotations: {sorted(expected - records.keys())}"
        )
    return records, audit


def stage_map(events):
    counts = Counter(e.stage for e in events)
    return {
        e.stage: e for e in events if counts[e.stage] == 1 and e.start_h is not None
    }


def prior_features(events, stage):
    """Clock and elapsed time since each strictly earlier observed stage."""
    cutoff = events[stage]
    earlier = []
    for name in STAGES[: STAGES.index(stage)]:
        event = events.get(name)
        if event and event.first < cutoff.first and event.start_h < cutoff.start_h:
            earlier.append(cutoff.start_h - event.start_h)
        else:
            earlier.append(float("nan"))
    return [cutoff.start_h, *earlier]
