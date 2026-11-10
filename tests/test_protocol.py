import csv
import tempfile
import unittest
from pathlib import Path

import numpy as np

from first_four_cells.evaluation import evaluate, make_folds, read_table
from first_four_cells.protocol import LANDMARKS

ROOT = Path(__file__).resolve().parents[1]


class ExperimentTests(unittest.TestCase):
    def test_inputs_available_at_cutoff(self):
        expected = {"t2": {"t2_h"}, "t3": {"t3_h", "two_cell_h"},
                    "t4": {"t4_h", "two_cell_h", "three_cell_h"}}
        for stage in LANDMARKS:
            actual = {key for _, features in stage.models() for key in features}
            self.assertEqual(actual, expected[stage.event])

    def test_verified_groups_stay_together(self):
        ids = [f"embryo-{i}" for i in range(20)]
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "groups.csv"
            with path.open("w", newline="") as stream:
                writer = csv.writer(stream)
                writer.writerow(("embryo_id", "group_id"))
                writer.writerows((key, i // 2) for i, key in enumerate(ids))
            splits, groups = make_folds(ids, 42, path)
            for train, test in splits:
                self.assertFalse(set(groups[train]) & set(groups[test]))

    def test_predictions_cover_cohort_and_reproduce_metrics(self):
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "experiment"
            evaluate(ROOT / "data/processed/cohort.csv", output, 42)
            rows = read_table(output / "predictions.csv")
            metrics = read_table(output / "metrics.csv")
            folds = {}
            for metric in metrics:
                subset = [r for r in rows if (r["model"], r["stage"]) ==
                          (metric["model"], metric["stage"])]
                self.assertEqual(len(subset), 287)
                self.assertEqual(len({r["embryo_id"] for r in subset}), 287)
                for r in subset:
                    self.assertEqual(folds.setdefault(r["embryo_id"], r["fold"]), r["fold"])
                errors = [abs(float(r["observed_remaining_h"]) - float(r["predicted_remaining_h"]))
                          for r in subset]
                self.assertAlmostEqual(np.mean(errors), float(metric["mae_h"]))
