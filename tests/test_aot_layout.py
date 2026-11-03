"""AoT layout contract tests; no rendering, no internet, no API required."""
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "layouts" / "aot"))
import compose


class AoTLayoutTests(unittest.TestCase):
    def test_zones_do_not_overlap_and_gap_is_enough(self):
        self.assertEqual((compose.W, compose.H, compose.FPS), (1080, 1920, 30))
        self.assertEqual((compose.FRAME_X, compose.FRAME_Y, compose.FRAME_W, compose.FRAME_H), (48, 48, 984, 880))
        # Chip pixels start around y 1010 (centre ~1080, height 140), well
        # below the top frame ending at y 928, even though the transparent
        # strip container starts at y 915.
        self.assertLess(compose.FRAME_Y + compose.FRAME_H, 1010)
        self.assertEqual(compose.CHIP_Y + compose.CHIP_H, 1255)
        self.assertGreaterEqual(compose.MASCOT_Y - compose.BOB_PX - (compose.CHIP_Y + compose.CHIP_H), 20)

    def test_p2_guard_offset(self):
        self.assertEqual(compose.OFF, 0.08)

    def test_rows_never_mix_sentences_and_cap_at_three_words(self):
        words = [
            {"word": "a", "start": 0.0, "end": 0.3},
            {"word": "b", "start": 0.3, "end": 0.6},
            {"word": "c", "start": 0.6, "end": 0.9},
            {"word": "d", "start": 0.9, "end": 1.2},
            {"word": "e", "start": 2.0, "end": 2.3},
        ]
        rows = compose.build_rows(words, [1.5])
        self.assertEqual([[w["word"] for w in r] for r in rows], [["a", "b", "c"], ["d"], ["e"]])

    def test_cover_crop_and_pop(self):
        from PIL import Image
        im = compose.cover_crop(Image.new("RGB", (2000, 1000), "red"), 984, 784)
        self.assertEqual(im.size, (984, 784))
        self.assertEqual(compose.pop(0), 0)
        self.assertAlmostEqual(compose.pop(1), 1.0, places=6)
        self.assertGreater(compose.pop(0.5), 1.0)  # back-out overshoot

    def test_spec_and_example_job_are_valid(self):
        self.assertTrue((ROOT / "layouts" / "aot" / "SPEC.md").is_file())
        job = json.loads((ROOT / "layouts" / "aot" / "example" / "job.json").read_text())
        self.assertEqual(job["layout"], "aot-v001")
        _job, _dir, beats, _words, _vis = compose.load_job(ROOT / "layouts" / "aot" / "example" / "job.json")
        self.assertEqual(len(beats), 4)

    def test_readme_declares_aot_default(self):
        readme = (ROOT / "README.md").read_text()
        self.assertIn("layouts/aot/SPEC.md", readme)
        self.assertIn("AoT layout", readme)


if __name__ == "__main__":
    unittest.main(verbosity=2)
