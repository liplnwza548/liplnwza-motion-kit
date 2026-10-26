"""New-job caption timing and deterministic, crop-safe drift contracts."""
from __future__ import annotations

import json
import sys
import tempfile
import unittest
import wave
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "renderer"))
import kit


class CaptionMotionPolicyTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="_caption_motion_policy_", dir=ROOT / "tests")
        self.job_dir = Path(self.temp.name) / "jobs" / "theme-systems-test-01"
        self.job_dir.mkdir(parents=True)

    def tearDown(self):
        self.temp.cleanup()

    def write_job(self, words=None):
        words = words or [
            {"word": "TEST", "start": 0.2, "end": 1.62},
            {"word": "ONLY", "start": 1.65, "end": 2.15},
            {"word": "NEW", "start": 2.2, "end": 2.7},
            {"word": "JOB", "start": 2.75, "end": 3.25},
        ]
        rate = 48000
        signal = np.round(0.04 * 32767 * np.sin(2 * np.pi * 440 * np.arange(rate * 4) / rate)).astype("<i2")
        voice = self.job_dir / "inputs" / "test-voice.wav"
        voice.parent.mkdir(parents=True, exist_ok=True)
        with wave.open(str(voice), "wb") as out:
            out.setparams((1, 2, rate, 0, "NONE", "not compressed"))
            out.writeframes(signal.tobytes())
        (self.job_dir / "words.json").write_text(json.dumps(words) + "\n", encoding="utf-8")
        (self.job_dir / "visemes.json").write_text('[{"start":0,"shape":"AA"}]\n', encoding="utf-8")
        job = {
            "schema_version": 1,
            "render_policy_version": 1,
            "title": "TEST ONLY: timing and motion",
            "topic_label": "TEST ONLY",
            "duration": 4,
            "voice": "inputs/test-voice.wav",
            "words": "words.json",
            "visemes": "visemes.json",
            "footer": "TEST ONLY - NOT APPROVED",
            "sources": [],
            "scenes": [{
                "start": 0, "end": 4, "layout": "title", "title": "TEST ONLY",
                "body": "SYNTHETIC SYSTEM TEST", "pose": "explain",
            }],
        }
        (self.job_dir / "job.json").write_text(json.dumps(job, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        (self.job_dir / "approval.json").write_text(
            '{"status":"pending","job_digest":null,"evidence":null}\n', encoding="utf-8"
        )
        return job

    def test_new_job_caps_long_cue_and_expires_group_context_per_chip(self):
        job = self.write_job()
        intervals = kit.visible_caption_intervals(json.loads((self.job_dir / "words.json").read_text()))
        self.assertAlmostEqual(intervals[0][1] - intervals[0][0], 1.2)
        average = sum(end - start for start, end in intervals) / len(intervals)
        self.assertGreaterEqual(average, 0.4)
        self.assertLessEqual(average, 0.7)
        self.assertEqual(kit.visible_caption_indices(json.loads((self.job_dir / "words.json").read_text()), intervals, 0.3), [0])
        self.assertEqual(kit.visible_caption_indices(json.loads((self.job_dir / "words.json").read_text()), intervals, 1.45), [])
        self.assertEqual(kit.visible_caption_indices(json.loads((self.job_dir / "words.json").read_text()), intervals, 1.7), [1])
        self.assertTrue(kit.validate(job, self.job_dir)["valid"])

    def test_new_job_rejects_average_outside_policy_range(self):
        job = self.write_job([
            {"word": "A", "start": 0.1, "end": 0.3},
            {"word": "B", "start": 0.4, "end": 0.6},
            {"word": "C", "start": 0.7, "end": 0.9},
            {"word": "D", "start": 1.0, "end": 1.2},
        ])
        with self.assertRaisesRegex(ValueError, "0.4–0.7s per clip"):
            kit.validate(job, self.job_dir)

    def test_pre_policy_approved_job_keeps_legacy_render_policy(self):
        job = self.write_job()
        job.pop("render_policy_version")
        (self.job_dir / "job.json").write_text(json.dumps(job), encoding="utf-8")
        (self.job_dir / "approval.json").write_text('{"status":"approved"}\n', encoding="utf-8")
        self.assertFalse(kit.render_policy_enabled(job))

    def test_static_image_drift_is_repeatable_and_fits_inside_evidence_panel(self):
        first = kit.media_motion_transform(3.25, 90, "evidence-still", (850, 390))
        second = kit.media_motion_transform(3.25, 90, "evidence-still", (850, 390))
        self.assertEqual(first, second)
        dx, dy, scale = first
        self.assertGreaterEqual(scale, 1.0)
        self.assertLessEqual(scale, 1.02)
        self.assertLessEqual(abs(dx) + 850 * scale / 2, 920 / 2)
        self.assertLessEqual(abs(dy) + 390 * scale / 2, 460 / 2)
        self.assertNotEqual(first, kit.media_motion_transform(3.5, 90, "evidence-still", (850, 390)))

    def test_decoration_drift_skips_text_and_evidence_zones(self):
        evidence = {"center_px": [980, 360], "size_px": 68, "motion": "drift"}
        empty_corner = {"center_px": [975, 1505], "size_px": 46, "motion": "drift"}
        self.assertFalse(kit.decoration_is_safe(evidence, {"media": {"role": "evidence"}}))
        self.assertTrue(kit.decoration_is_safe(empty_corner, {"layout": "list"}))
        self.assertFalse(kit.decoration_is_safe(empty_corner, {"layout": "summary", "cta": "ข้อความที่ได้รับอนุมัติ"}))


if __name__ == "__main__":
    unittest.main(verbosity=2)
