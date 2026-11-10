"""Index extracted focal planes for stage classification, event detection and video models.

Run from the project root with python -m first_four_cells.analyses.imaging.frame_index.
"""

import argparse
import csv
import gzip
import re
from bisect import bisect_right
from pathlib import Path
from tempfile import TemporaryDirectory

from ..events import inspect

RUN = re.compile(r"_RUN(\d+)\.jpe?g$", re.IGNORECASE)
PLANES = (
    "embryo_dataset",
    "embryo_dataset_F-15",
    "embryo_dataset_F-30",
    "embryo_dataset_F-45",
    "embryo_dataset_F15",
    "embryo_dataset_F30",
    "embryo_dataset_F45",
)


def label_frame(events, starts, frame):
    position = bisect_right(starts, frame) - 1
    if position < 0 or events[position].last < frame:
        return ""
    return events[position].stage


def build(data, image_root, output):
    records, _ = inspect(data)
    planes = [image_root / name for name in PLANES if (image_root / name).is_dir()]
    if not planes:
        raise ValueError(
            f"No extracted Nantes image plane directories under {image_root}"
        )
    output.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    with TemporaryDirectory(dir=output.parent) as tmp:
        staged = Path(tmp) / "frames.gz"
        with gzip.open(staged, "wt", newline="", encoding="utf-8") as handle:
            writer = csv.writer(handle)
            writer.writerow(
                ("embryo_id", "plane", "frame", "annotated_stage", "image_path")
            )
            for embryo, events in records.items():
                starts = [e.first for e in events]
                if any(a.last >= b.first for a, b in zip(events, events[1:])):
                    raise ValueError(f"Overlapping phase labels in {embryo}")
                for plane in planes:
                    directory = plane / embryo
                    if not directory.is_dir():
                        continue
                    seen = set()
                    for file in sorted(directory.iterdir()):
                        match = RUN.search(file.name)
                        if not match or not file.is_file():
                            continue
                        frame = int(match[1])
                        if frame in seen:
                            raise ValueError(f"Duplicate RUN{frame} in {directory}")
                        seen.add(frame)
                        writer.writerow(
                            (
                                embryo,
                                plane.name,
                                frame,
                                label_frame(events, starts, frame),
                                file.relative_to(image_root).as_posix(),
                            )
                        )
                        count += 1
        if not count:
            raise ValueError("No matching RUN images found.")
        staged.replace(output)
    return count


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", type=Path, default=Path("data"))
    parser.add_argument("--image-root", type=Path, default=Path("data/raw"))
    parser.add_argument(
        "--output", type=Path, default=Path("data/processed/frames.csv.gz")
    )
    args = parser.parse_args()
    print(f"Indexed {build(args.data, args.image_root, args.output)} image paths.")
