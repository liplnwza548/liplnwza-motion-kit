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


class AoTWidgetTests(unittest.TestCase):
    def _blank_frame(self):
        from PIL import Image
        return Image.new("RGB", (compose.W, compose.H), (255, 255, 255))

    def _dark_rows(self, frame, x0, x1, y0, y1):
        px = frame.load()
        return [y for y in range(y0, y1) for x in range(x0, x1)
                if px[x, y][0] < 60 and px[x, y][1] < 60 and px[x, y][2] < 60]

    def test_draw_text_above_leaves_gap(self):
        from PIL import ImageDraw
        frame = self._blank_frame()
        d = ImageDraw.Draw(frame)
        bottom = compose.draw_text_above(d, 540, 600, "งานทั้งหมด", compose.font(44), compose.INK)
        self.assertEqual(bottom, 588)
        self.assertFalse(self._dark_rows(frame, 200, 900, 589, 599),
                         "ink must not reach into the 12px gap above the box")

    def test_container_labels_sit_above_boxes_with_clear_gap(self):
        # Procrastination B05 data, phase 1 (u=0.125).
        beat = {"name": "B05", "start": 0.0, "end": 4.0, "widgets": [
            {"type": "container", "start": 0.0, "end": 4.0,
             "items": ["งานค้าง", "การบ้าน", "เป้าหมาย"],
             "box": "งานทั้งหมด", "target": "กองไว้ก่อน"}]}
        frame = self._blank_frame()
        compose.widget_frame(frame, beat, 0.5)
        # Box top y=530 (centre x=363), target top y=520 (centre x=776).
        # Check each label in its own x-window, so the other box's top
        # edge cannot intrude into this label's gap band.
        for top, cx, half in ((530, 363, 160), (520, 776, 140)):
            self.assertTrue(self._dark_rows(frame, cx - half, cx + half, top - 60, top - 12),
                            f"label ink missing above box top {top}")
            self.assertFalse(self._dark_rows(frame, cx - half, cx + half, top - 11, top - 2),
                             f"ink touches box top {top} — the gap must be clear")

    def test_typewriter_box_is_content_sized_and_bottom_anchored(self):
        beat = {"name": "B07", "start": 0.0, "end": 3.0, "widgets": [
            {"type": "typewriter", "start": 0.0, "end": 3.0,
             "text": "กฎ 2 นาที: เริ่มให้ได้ก่อน"}]}
        frame = self._blank_frame()
        compose.widget_frame(frame, beat, 2.9)  # full text typed
        px = frame.load()
        # Cream box pixels on a column clear of the text and the tick
        # badge (the badge's cream checkmark sticks below the box).
        ys = [y for y in range(144, 928) if px[150, y] == (255, 253, 246)]
        self.assertTrue(ys, "typewriter box not drawn")
        top, bottom = min(ys), max(ys)
        self.assertLess(bottom - top, 200, "box must be content-sized, not the old 260px slab")
        self.assertAlmostEqual(bottom, 900, delta=3,
                               msg="box bottom fill must sit ~24px above panel bottom (928); "
                                   "the 4px outline occupies the last 4px")
        self.assertGreater(top, 536, "box must not cover the panel centre (focal point)")

    def test_two_panel_widgets_in_one_beat_fail(self):
        beat = {"name": "B", "widgets": [
            {"type": "container", "items": ["a"], "box": "b", "target": "t"},
            {"type": "typewriter", "text": "x"}]}
        with self.assertRaises(ValueError):
            compose.validate_widgets(beat)

    def test_highlight_plus_one_panel_widget_passes(self):
        beat = {"name": "B", "widgets": [
            {"type": "highlight"},
            {"type": "cta", "profile": "P", "keyword": "k"}]}
        compose.validate_widgets(beat)  # must not raise

    def test_typewriter_text_too_long_fails(self):
        beat = {"name": "B", "widgets": [
            {"type": "typewriter", "text": "คำยาว " * 40}]}
        with self.assertRaises(ValueError):
            compose.validate_widgets(beat)

    def test_container_items_too_wide_fail(self):
        beat = {"name": "B", "widgets": [
            {"type": "container", "items": ["คำยาวมากๆๆๆๆๆๆๆๆๆๆๆๆๆๆๆๆๆๆๆๆ"] * 6,
             "box": "b", "target": "t"}]}
        with self.assertRaises(ValueError):
            compose.validate_widgets(beat)


    def test_cta_show_panel_false_does_not_draw_panel_card(self):
        beat = {"name": "B08", "start": 0.0, "end": 4.0, "widgets": [
            {"type": "cta", "start": 0.0, "end": 4.0,
             "profile": "LipInwZa", "keyword": "หลอกสมอง",
             "show_panel": False, "below_mascot": True}]}
        frame = self._blank_frame()
        compose.widget_frame(frame, beat, 1.0)
        # Panel centre (x=540, y=536): no white card pixels should exist
        px = frame.load()
        panel_pixels = [px[x, y] for x in range(300, 780, 50) for y in range(300, 700, 50)]
        self.assertNotIn((255, 253, 246), panel_pixels, "CTA panel card drawn despite show_panel=False")

    def test_cta_show_panel_false_not_counted_as_panel_widget(self):
        beat = {"name": "B", "widgets": [
            {"type": "container", "items": ["a"], "box": "b", "target": "t"},
            {"type": "cta", "profile": "P", "keyword": "k", "show_panel": False}]}
        compose.validate_widgets(beat)  # must not raise

    def test_cta_show_panel_true_plus_container_fails(self):
        beat = {"name": "B", "widgets": [
            {"type": "container", "items": ["a"], "box": "b", "target": "t"},
            {"type": "cta", "profile": "P", "keyword": "k", "show_panel": True}]}
        with self.assertRaises(ValueError):
            compose.validate_widgets(beat)

    def test_cta_pill_drawn_when_show_panel_false(self):
        beat = {"name": "B08", "start": 0.0, "end": 4.0, "widgets": [
            {"type": "cta", "start": 0.0, "end": 4.0,
             "profile": "LipInwZa", "keyword": "หลอกสมอง", "pill": "ป้าย",
             "show_panel": False, "below_mascot": True}]}
        frame = self._blank_frame()
        compose.cta_pill_frame(frame, beat, 1.0)
        px = frame.load()
        # Pill is drawn at y=1852 in the below-mascot strip
        pill_pixels = [px[x, 1860] for x in range(300, 780, 20)]
        self.assertIn((255, 214, 72), pill_pixels, "CTA pill missing below mascot")


if __name__ == "__main__":
    unittest.main(verbosity=2)
