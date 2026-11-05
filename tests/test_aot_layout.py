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
        # Mascot bottom anchor (1872, A-fixed) sits well below the chip
        # strip end; its top varies per pose/viseme, so the gap itself
        # is a frame-QC check, not a static assert.
        self.assertGreaterEqual(compose.MASCOT_BOTTOM_Y - compose.BOB_PX - (compose.CHIP_Y + compose.CHIP_H), 20)

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
        # Locked spring (2026-11-05): 0.6x at u=0, ~1.08x overshoot
        # mid-way, 1.0x at u=1 (spring_scale replaced the old pop()).
        self.assertAlmostEqual(compose.spring_scale(0), 0.6, places=6)
        self.assertAlmostEqual(compose.spring_scale(1), 1.0, places=6)
        self.assertGreater(compose.spring_scale(0.5), 1.0)  # back-out overshoot

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


class AoTWordsGateTests(unittest.TestCase):
    """Phase 1 gates + Phase 3 Thai fixes (fix/aot-words-thai-gates).

    The 2026-11-05 procrastination job's words.json was 37 hand-written
    phrases with times guessed from character length. These tests pin
    the behaviour that must have failed that job, while the checked-in
    example job (real short words, MFA-style times) must still pass.
    """

    PROCRASTINATION_PHRASES = [
        "เคยสงสัยไหมครับ", "ทำไมเราถึง", "ชอบเลื่อนงาน",
        "วิทยาศาสตร์บอกว่า", "เราขี้เกียจเลยครับ",
        "ระหว่างสมองส่วนอารมณ์", "สมองส่วนเหตุผล",
        "ทำให้สมองส่วนหน้า", "หลอกสมองครับ",
    ]

    def _words(self, texts, dur=0.5):
        t = 0.0
        out = []
        for text in texts:
            out.append({"word": text, "start": round(t, 3), "end": round(t + dur, 3)})
            t += dur + 0.02
        return out

    def test_example_words_pass_the_gates(self):
        words = json.loads((ROOT / "layouts" / "aot" / "example" / "words_roles.json").read_text())
        compose.validate_words(words)  # must not raise

    def test_phrase_chips_fail_the_gates(self):
        with self.assertRaisesRegex(ValueError, "one short word"):
            compose.validate_words(self._words(self.PROCRASTINATION_PHRASES))

    def test_single_long_phrase_fails(self):
        with self.assertRaisesRegex(ValueError, "one short word"):
            compose.validate_words(self._words(["ระหว่างสมองส่วนอารมณ์"]))

    def test_non_monotonic_times_fail(self):
        words = [
            {"word": "เรา", "start": 0.0, "end": 0.3},
            {"word": "เห็น", "start": 0.2, "end": 0.5},
        ]
        with self.assertRaisesRegex(ValueError, "monotonic"):
            compose.validate_words(words)

    def test_overlong_chip_duration_fails(self):
        with self.assertRaisesRegex(ValueError, "1.2"):
            compose.validate_words([{"word": "เรา", "start": 0.0, "end": 1.5}])

    def test_provenance_required_for_real_jobs(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            words_path = tmp / "words.json"
            words_path.write_text(json.dumps(self._words(["เรา", "เห็น"]), ensure_ascii=False), encoding="utf-8")
            job = {"voice": "voice.wav"}
            with self.assertRaisesRegex(ValueError, "provenance missing"):
                compose.validate_words_provenance(
                    self._words(["เรา", "เห็น"]), words_path, tmp, job)
            # The checked-in example is the only exemption.
            self.assertIsNone(compose.validate_words_provenance(
                self._words(["เรา", "เห็น"]), words_path, tmp, {"fixture": True}))

    def test_provenance_chip_count_must_match(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            words = self._words(["เรา", "เห็น"])
            words_path = tmp / "words.json"
            words_path.write_text(json.dumps(words, ensure_ascii=False), encoding="utf-8")
            (tmp / "words.provenance.json").write_text(json.dumps(
                {"chips": 99, "mfa_model": "thai_mfa"}), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "chip count"):
                compose.validate_words_provenance(words, words_path, tmp, {"voice": "voice.wav"})
            (tmp / "words.provenance.json").write_text(json.dumps(
                {"chips": 2, "mfa_model": "thai_mfa"}), encoding="utf-8")
            self.assertIsNone(compose.validate_words_provenance(
                words, words_path, tmp, {"voice": "voice.wav"}))

    def test_grapheme_clusters_keep_stacked_marks_together(self):
        self.assertEqual(compose.grapheme_clusters("ซื้อ"), ["ซื้", "อ"])
        self.assertEqual(compose.grapheme_clusters("รื้อฟื้น"), ["รื้", "อ", "ฟื้", "น"])
        # Slicing by cluster never leaves a bare sara/tone mark behind.
        self.assertEqual(compose.grapheme_slice("ซื้อ", 1), "ซื้")
        self.assertEqual(compose.grapheme_slice("เริ่มให้ได้ก่อน", 2), "เริ่")
        import unicodedata
        for text in ["ซื้อ", "รื้อฟื้น", "เริ่มให้ได้ก่อน"]:
            clusters = compose.grapheme_clusters(text)
            # Every cluster starts with a base character, never a mark.
            for cluster in clusters:
                self.assertEqual(unicodedata.combining(cluster[0]), 0)
            # Codepoint slicing, the old bug, truncates a cluster:
            # "ซื้อ"[:2] is "ซื", missing the tone mark of "ซื้".
            self.assertNotEqual(text[:2], compose.grapheme_slice(text, 1))

    def test_thai_shaping_is_available(self):
        compose.check_thai_shaping()  # must not raise on this machine
        fnt = compose.font(80)
        bb = fnt.getbbox("ซื้อ")
        self.assertGreater(bb[2] - bb[0], 0)

    def test_chip_baselines_align_across_stacked_and_plain_words(self):
        # Baseline anchoring: every chip's ink bottom must sit on the
        # same line. Bbox-centring put "ซื้อ" (ink bottom 113) 20px
        # below "หลอกสมอง" (ink bottom 93) in the same row.
        from PIL import Image, ImageDraw
        bottoms = []
        for word in ["ซื้อ", "หลอกสมอง", "เรื่องนี้", "ไม่ใช่เพราะ"]:
            fnt = compose.font(80)
            chip = Image.new("RGBA", (600, 140), (0, 0, 0, 0))
            d = ImageDraw.Draw(chip)
            d.text((300, compose.baseline_y_for_centre(fnt, 70)), word,
                   font=fnt, fill=(0, 0, 0, 255), anchor="ms")
            bottoms.append(chip.split()[3].getbbox()[3])
        self.assertEqual(len(set(bottoms)), 1, f"ink bottoms differ: {bottoms}")


if __name__ == "__main__":
    unittest.main(verbosity=2)
