"""Evaluate timing models with shared folds and paired held-out errors."""
import csv
import hashlib
import json
from pathlib import Path
from tempfile import TemporaryDirectory

import numpy as np
import sklearn
from sklearn.linear_model import LinearRegression
from sklearn.model_selection import GroupKFold, KFold

from .protocol import LANDMARKS


def read_table(path):
    with path.open(newline="", encoding="utf-8-sig") as stream:
        return list(csv.DictReader(stream))


def write_table(path, rows):
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def load_cohort(path):
    rows = sorted(read_table(path), key=lambda row: row["embryo_id"])
    ids = [row["embryo_id"] for row in rows]
    if len(ids) < 5 or len(set(ids)) != len(ids) or any(not i.strip() for i in ids):
        raise ValueError("Five-fold evaluation requires unique embryo IDs and at least five rows.")
    times = np.array([[float(row[k]) for k in ("t2_h", "t3_h", "t4_h", "tB_h")]
                      for row in rows])
    intervals = np.diff(times, axis=1)
    if not np.isfinite(times).all() or (intervals <= 0).any():
        raise ValueError("Each embryo must have finite, strictly increasing event times.")
    for j, key in enumerate(("two_cell_h", "three_cell_h", "remaining_h")):
        if not np.allclose(intervals[:, j], [float(row[key]) for row in rows], rtol=0, atol=1e-8):
            raise ValueError(f"Inconsistent derived column: {key}")
    return ids, rows


def make_folds(ids, seed, group_file):
    groups = np.array(ids)
    if group_file:
        mapping = read_table(group_file)
        lookup = {r["embryo_id"]: r["group_id"].strip() for r in mapping}
        if len(lookup) != len(mapping) or any(not lookup.get(i) for i in ids):
            raise ValueError("Supply exactly one verified group per eligible embryo.")
        groups = np.array([lookup[i] for i in ids])
        splits = GroupKFold(5).split(ids, groups=groups)
    else:
        splits = KFold(5, shuffle=True, random_state=seed).split(ids)
    return list(splits), groups


def paired_interval(difference, groups, seed, draws=5000):
    # Sample whole groups. Weight each resampled embryo equally in the mean.
    _, index = np.unique(groups, return_inverse=True)
    totals = np.bincount(index, weights=difference)
    sizes = np.bincount(index)
    rng = np.random.default_rng(seed)
    means = []
    for _ in range(draws):
        sample = rng.integers(len(sizes), size=len(sizes))
        means.append(totals[sample].sum() / sizes[sample].sum())
    return np.quantile(means, [0.025, 0.975]).tolist()


def evaluate(cohort: Path, output: Path, seed: int, group_file: Path | None = None):
    ids, rows = load_cohort(cohort)
    splits, groups = make_folds(ids, seed, group_file)
    folds = np.empty(len(ids), dtype=int)
    for number, (_, test) in enumerate(splits, start=1):
        folds[test] = number

    predictions, metrics, comparisons = [], [], []
    for stage in LANDMARKS:
        clock = np.array([float(row[stage.clock]) for row in rows])
        target = np.array([float(row["tB_h"]) for row in rows]) - clock
        errors = {}
        for model, features in stage.models():
            x = np.array([[float(row[k]) for k in features] for row in rows])
            predicted = np.empty(len(ids))
            for train, test in splits:
                if features:
                    fit = LinearRegression().fit(x[train], target[train])
                    predicted[test] = fit.predict(x[test])
                else:
                    predicted[test] = np.median(target[train])
            errors[model] = np.abs(target - predicted)
            metrics.append(dict(stage=stage.event, model=model, n=len(ids),
                                mae_h=errors[model].mean()))
            for i, embryo in enumerate(ids):
                predictions.append(dict(embryo_id=embryo, fold=folds[i], stage=stage.event,
                                        model=model, observed_remaining_h=target[i],
                                        predicted_remaining_h=predicted[i],
                                        predicted_tB_h=clock[i] + predicted[i]))
        if "rhythm" in errors:
            difference = errors["clock"] - errors["rhythm"]
            low, high = paired_interval(difference, groups, seed)
            comparisons.append(dict(stage=stage.event, gain_h=difference.mean(),
                                    ci_low_h=low, ci_high_h=high))

    metadata = dict(seed=seed, folds=5, fold_unit="verified_group" if group_file else "embryo",
                    bootstrap_draws=5000, cohort_sha256=hashlib.sha256(cohort.read_bytes()).hexdigest(),
                    numpy=np.__version__, sklearn=sklearn.__version__)
    output.parent.mkdir(parents=True, exist_ok=True)
    if output.exists():
        raise FileExistsError(f"Choose a new run directory: {output}")
    with TemporaryDirectory(dir=output.parent) as tmp:
        run = Path(tmp) / "run"
        run.mkdir()
        write_table(run / "predictions.csv", predictions)
        write_table(run / "metrics.csv", metrics)
        write_table(run / "paired_gain.csv", comparisons)
        (run / "run.json").write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
        run.rename(output)
