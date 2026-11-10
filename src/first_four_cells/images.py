"""Match the first annotated four-cell frame to the central-plane JPEG."""
import csv
import re
from pathlib import Path
from tempfile import NamedTemporaryFile

from PIL import Image

from .cohort import read_starts


def build_manifest(cohort: Path, annotations: Path, images: Path, output: Path):
    if not annotations.is_dir() or not any(annotations.glob("*_phases.csv")):
        raise ValueError(f"Expected extracted phase CSVs in {annotations}")
    if not images.is_dir() or images.name.startswith("embryo_dataset_F"):
        raise ValueError(f"Expected the extracted central-plane embryo_dataset folder: {images}")

    with cohort.open(newline="", encoding="utf-8-sig") as stream:
        ids = [row["embryo_id"] for row in csv.DictReader(stream)]
    if not ids or len(set(ids)) != len(ids) or any(
        not re.fullmatch(r"[A-Za-z0-9_-]+", embryo) for embryo in ids
    ):
        raise ValueError("Expected unique embryo identifiers in the cohort CSV.")

    rows = []
    for embryo in ids:
        annotation = annotations / f"{embryo}_phases.csv"
        frame = read_starts(annotation).get("t4") if annotation.is_file() else None
        path = None
        if frame is None:
            status = "missing_t4" if annotation.is_file() else "missing_annotation"
        else:
            folder = images / embryo
            pattern = re.compile(rf"_RUN0*{frame}\.jpe?g$", re.IGNORECASE)
            matches = [p for p in folder.iterdir() if p.is_file() and pattern.search(p.name)] if folder.is_dir() else []
            if len(matches) == 1:
                path = matches[0]
                try:
                    with Image.open(path) as image:
                        image.load()
                    status = "ok"
                except (OSError, ValueError):
                    status = "unreadable_image"
            else:
                status = "ambiguous_frame" if matches else "missing_image"
        rows.append((embryo, frame, path.relative_to(images).as_posix() if path else "", status))

    output.parent.mkdir(parents=True, exist_ok=True)
    with NamedTemporaryFile(mode="w", newline="", encoding="utf-8", dir=output.parent,
                            delete=False) as stream:
        tmp = Path(stream.name)
        try:
            writer = csv.writer(stream)
            writer.writerow(("embryo_id", "t4_start_frame", "image_path", "status"))
            writer.writerows(rows)
        except BaseException:
            stream.close()
            tmp.unlink(missing_ok=True)
            raise
    try:
        tmp.replace(output)
    finally:
        tmp.unlink(missing_ok=True)
    usable = sum(row[-1] == "ok" for row in rows)
    return usable, len(rows)
