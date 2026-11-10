import csv
import tempfile
import unittest
from pathlib import Path

from PIL import Image
from first_four_cells.images import build_manifest


class ImageManifestTest(unittest.TestCase):
    def test_exact_first_frame_and_exclusions(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            annotations = root / "annotations"
            annotations.mkdir()
            images = root / "embryo_dataset"
            cohort = root / "cohort.csv"
            cohort.write_text("embryo_id\nA-1\nB-1\nC-1\nD-1\n")
            for embryo in ("A-1", "B-1", "C-1", "D-1"):
                folder = images / embryo
                folder.mkdir(parents=True)
                (annotations / f"{embryo}_phases.csv").write_text("t4,7,11\n")
                Image.new("L", (8, 8)).save(folder / "demo_RUN70.jpeg")
            for embryo in ("A-1", "D-1"):
                Image.new("L", (8, 8)).save(images / embryo / "demo_RUN7.jpeg")
            Image.new("L", (8, 8)).save(images / "D-1/other_RUN007.jpeg")
            (images / "C-1/demo_RUN7.jpeg").write_bytes(b"broken")
            out = root / "out.csv"
            self.assertEqual(build_manifest(cohort, annotations, images, out), (1, 4))
            with out.open() as stream:
                rows = list(csv.DictReader(stream))
            self.assertEqual([r["status"] for r in rows],
                             ["ok", "missing_image", "unreadable_image", "ambiguous_frame"])
            self.assertEqual(rows[0]["image_path"], "A-1/demo_RUN7.jpeg")
