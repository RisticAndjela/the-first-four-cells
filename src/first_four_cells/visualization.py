"""Generate an offline explorer from a cohort and held-out t4 predictions."""
import base64
import csv
import io
import json
import math
import os
from pathlib import Path
from tempfile import NamedTemporaryFile

from PIL import Image


def records(path):
    with path.open(encoding="utf-8-sig", newline="") as stream:
        return list(csv.DictReader(stream))


def report(cohort, predictions, manifest, images, output):
    embryos = {}
    for row in records(cohort):
        key = row["embryo_id"]
        times = [float(row[k]) for k in ("t2_h", "t3_h", "t4_h", "tB_h")]
        if key in embryos or not all(map(math.isfinite, times)) or sorted(set(times)) != times:
            raise ValueError(f"Invalid cohort entry: {key}")
        embryos[key] = dict(id=key, times=times, predictions={})

    for row in records(predictions):
        model = row["model"]
        if row["stage"] != "t4" or model not in ("clock", "rhythm"):
            continue
        item = embryos[row["embryo_id"]]
        t4, tb = item["times"][2:]
        estimate = float(row["predicted_tB_h"])
        if (model in item["predictions"] or not math.isfinite(estimate)
                or not math.isclose(float(row["observed_remaining_h"]), tb - t4, abs_tol=1e-6)):
            raise ValueError(f"Inconsistent prediction: {item['id']} {model}")
        item["predictions"][model] = estimate
    if len(embryos) < 2 or any(len(e["predictions"]) != 2 for e in embryos.values()):
        raise ValueError("Expected paired t4 forecasts for every cohort embryo.")

    if manifest.is_file():
        root = images.resolve()
        for row in records(manifest):
            if row["status"] != "ok":
                continue
            item = embryos.get(row["embryo_id"])
            path = (root / row["image_path"]).resolve()
            if item is None or not path.is_relative_to(root) or not path.is_file():
                continue
            with Image.open(path) as image:
                thumb = image.convert("L")
                thumb.thumbnail((320, 320))
                buffer = io.BytesIO()
                thumb.save(buffer, format="JPEG", quality=85)
            item["image"] = base64.b64encode(buffer.getvalue()).decode("ascii")
            item["frame"] = int(row["t4_start_frame"])

    data = json.dumps(list(embryos.values()), allow_nan=False).replace("<", r"\u003c")
    page = Path(__file__).with_name("explorer.html").read_text(encoding="utf-8")
    output.parent.mkdir(parents=True, exist_ok=True)
    with NamedTemporaryFile(dir=output.parent, delete=False) as temp:
        name = temp.name
    try:
        Path(name).write_text(page.replace("/*COHORT_DATA*/", data), encoding="utf-8")
        os.replace(name, output)
    finally:
        Path(name).unlink(missing_ok=True)
