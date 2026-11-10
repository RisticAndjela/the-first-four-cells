import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from first_four_cells.analyses.events import Event, inspect, prior_features, stage_map
from first_four_cells.analyses.trajectories import describe


class ResearchTests(unittest.TestCase):
    def test_embryo_level_join_uses_frame_key_and_preserves_unknown_onsets(self):
        with TemporaryDirectory() as raw:
            root = Path(raw)
            for name in ("embryo_dataset_annotations", "embryo_dataset_time_elapsed"):
                (root / name / name).mkdir(parents=True)
            a = next(root.glob("embryo_dataset_annotations/*"))
            t = next(root.glob("embryo_dataset_time_elapsed/*"))
            (a / "A-2-4_phases.csv").write_text("t2,1,2\nt4,4,6\ntB,8,9\n")
            (t / "A-2-4_timeElapsed.csv").write_text(
                "frame_index,time\n1,20\n4,40\n6,43\n"
            )
            data, audit = inspect(root)
            events = stage_map(data["A-2-4"])
            self.assertEqual(events["t4"].start_h, 40)
            self.assertNotIn("tB", events)
            self.assertEqual(audit[0]["orphan_starts"], 1)
            self.assertEqual(len(describe(data)["pair_support"]), 120)

    def test_later_annotation_cannot_change_earlier_landmark_features(self):
        import numpy as np

        early = [Event("t2", 1, 4, 20, 24), Event("t4", 5, 8, 30, 34)]
        later = [Event("t3", 6, 7, 31, 33), Event("tB", 200, 210, 110, 120)]
        np.testing.assert_equal(
            prior_features(stage_map(early), "t4"),
            prior_features(stage_map(early + later), "t4"),
        )


class FrameIndexTests(unittest.TestCase):
    def test_gaps_and_inclusive_phase_endpoints(self):
        from first_four_cells.analyses.imaging.frame_index import label_frame

        events = [Event("t2", 3, 5, None, None), Event("t4", 8, 9, None, None)]
        self.assertEqual(
            [label_frame(events, [3, 8], f) for f in (2, 3, 5, 6, 8, 10)],
            ["", "t2", "t2", "", "t4", ""],
        )