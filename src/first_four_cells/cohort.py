"""Build the embryo timing cohort from the two extracted Zenodo v3 archives."""

import csv
from collections import Counter
from decimal import Decimal
from pathlib import Path
from tempfile import TemporaryDirectory

EVENTS = ("t2", "t3", "t4", "tB")
COLUMNS = ("embryo_id", "t2_h", "t3_h", "t4_h", "tB_h", "two_cell_h",
           "three_cell_h", "remaining_h")


def increasing(values):
    return all(left < right for left, right in zip(values, values[1:]))


def read_starts(path):
    starts = {}
    with path.open(newline="") as stream:
        for row in csv.reader(stream):
            if not row:
                continue
            event, start, _ = row
            if event in EVENTS:
                starts[event] = min(int(start), starts.get(event, int(start)))
    return starts


def match_times(path, frames):
    if not path.is_file():
        return None, "missing_timestamp_file"
    times = {}
    with path.open(newline="") as stream:
        for row in csv.DictReader(stream):
            index = int(row["frame_index"])
            if index in frames:
                time = Decimal(row["time"])
                if not time.is_finite():
                    return None, f"invalid_time_at_frame_{index}"
                if index in times and times[index] != time:
                    return None, f"conflicting_time_at_frame_{index}"
                times[index] = time
    for frame in frames:
        if frame not in times:
            return None, f"missing_time_at_frame_{frame}"
    ordered = [times[frame] for frame in frames]
    if not increasing(ordered):
        return None, "timestamps_out_of_order"
    return ordered, None


def build(raw: Path, output: Path) -> None:
    annotations = sorted((raw / "embryo_dataset_annotations").glob("*_phases.csv"))
    clocks = raw / "embryo_dataset_time_elapsed"
    if not annotations or not any(clocks.glob("*_timeElapsed.csv")):
        raise SystemExit(f"Extract both Zenodo archives under {raw} (see README.md).")

    cohort, exclusions = [], []
    counts = Counter()
    for path in annotations:
        embryo = path.name.removesuffix("_phases.csv")
        starts = read_starts(path)
        counts["t4"] += "t4" in starts
        counts["t4_then_tB"] += ("t4" in starts and "tB" in starts
                                  and starts["t4"] < starts["tB"])
        missing = [event for event in EVENTS if event not in starts]
        if missing:
            exclusions.append((embryo, "missing_events:" + ",".join(missing)))
            continue
        frames = [starts[event] for event in EVENTS]
        if not increasing(frames):
            exclusions.append((embryo, "event_frames_out_of_order"))
            continue
        counts["ordered_events"] += 1
        times, reason = match_times(clocks / f"{embryo}_timeElapsed.csv", frames)
        if reason:
            exclusions.append((embryo, reason))
            continue
        t2, t3, t4, tb = times
        cohort.append((embryo, *times, t3 - t2, t4 - t3, tb - t4))

    output.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory(dir=output) as staging:
        for name, header, rows in [
            ("cohort.csv", COLUMNS, cohort),
            ("exclusions.csv", ("embryo_id", "reason"), exclusions),
        ]:
            with (Path(staging) / name).open("w", newline="", encoding="utf-8") as stream:
                writer = csv.writer(stream)
                writer.writerow(header)
                writer.writerows(rows)
        for name in ("cohort.csv", "exclusions.csv"):
            (Path(staging) / name).replace(output / name)
    print(f"Annotated: {len(annotations)} | t4: {counts['t4']} | "
          f"t4 then tB: {counts['t4_then_tB']} | ordered events: {counts['ordered_events']} | "
          f"included: {len(cohort)} | excluded: {len(exclusions)}")
