"""Regression coverage for QC and input contracts using generated fixtures only."""
from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "renderer"))
import kit


class ReliabilityRegressionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="_reliability_test_", dir=ROOT / "tests")
        self.tmp = Path(self.temp.name)

    def tearDown(self):
        self.temp.cleanup()

    def test_qc_rejects_wrong_video_dimensions_in_normal_and_optimized_python(self):
        video = self.tmp / "wrong-size.mp4"
        subprocess.run([
            "ffmpeg", "-y", "-v", "error",
            "-f", "lavfi", "-i", "color=c=black:s=540x960:r=30:d=5",
            "-f", "lavfi", "-i", "sine=frequency=440:sample_rate=48000:duration=5",
            "-filter:a", "volume=2.0", "-c:v", "libx264", "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-ac", "2", "-t", "5", str(video),
        ], check=True)

        for optimize in (False, True):
            (self.tmp / "qc.json").write_text('{"technical_pass":true}\n', encoding="utf-8")
            command = [sys.executable]
            if optimize:
                command.append("-O")
            command.extend([str(ROOT / "renderer" / "kit.py"), "qc", str(video)])
            with self.subTest(optimized=optimize):
                result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True)
                self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
                self.assertNotIn('"technical_pass": true', result.stdout)
                self.assertIn("1080x1920", result.stderr)
                report = json.loads((self.tmp / "qc.json").read_text(encoding="utf-8"))
                self.assertIs(report["technical_pass"], False)
                self.assertTrue(any("1080x1920" in error for error in report["errors"]))

    def test_empty_visemes_are_rejected_during_validation(self):
        source = ROOT / "examples" / "benchmark15"
        job_dir = self.tmp / "benchmark15"
        shutil.copytree(source, job_dir, ignore=shutil.ignore_patterns("reference", "output*", "media_cache"))
        job = kit.read(job_dir / "job.json")
        job["scenes"][1]["media"]["path"] = str(ROOT / "assets" / "illustrations" / "red_car.png")
        kit.write(job_dir / "job.json", job)
        visemes = job_dir / "visemes.json"
        visemes.write_text("[]\n", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "viseme cues are required"):
            kit.validate(job, job_dir)

    def test_qc_reports_missing_video_or_audio_stream_without_traceback(self):
        fixtures = {
            "audio-only.mp4": (
                "video",
                ["-f", "lavfi", "-i", "sine=frequency=440:sample_rate=48000:duration=5", "-c:a", "aac", "-b:a", "192k"],
            ),
            "video-only.mp4": (
                "audio",
                ["-f", "lavfi", "-i", "color=c=black:s=1080x1920:r=30:d=5", "-an", "-c:v", "libx264", "-pix_fmt", "yuv420p"],
            ),
        }
        for name, (missing_stream, inputs) in fixtures.items():
            video = self.tmp / name
            subprocess.run(["ffmpeg", "-y", "-v", "error", *inputs, "-t", "5", str(video)], check=True)
            (self.tmp / "qc.json").write_text('{"technical_pass":true}\n', encoding="utf-8")
            result = subprocess.run(
                [sys.executable, str(ROOT / "renderer" / "kit.py"), "qc", str(video)],
                cwd=ROOT, capture_output=True, text=True,
            )
            with self.subTest(file=name):
                self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
                self.assertNotIn("Traceback", result.stderr)
                self.assertIn(f"Missing required {missing_stream} stream", result.stderr)
                report = json.loads((self.tmp / "qc.json").read_text(encoding="utf-8"))
                self.assertIs(report["technical_pass"], False)
                self.assertTrue(any(f"Missing required {missing_stream} stream" in error for error in report["errors"]))

    def test_manifest_covers_all_non_manifest_checkout_files(self):
        tracked = subprocess.check_output([
            "git", "-c", "core.quotePath=false", "ls-files", "--cached", "--others", "--exclude-standard", "-z",
        ], cwd=ROOT)
        checkout_files = {item for item in tracked.decode("utf-8").split("\0") if item}
        manifest_path = ROOT / "manifest-sha256.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        self.assertEqual(set(manifest), checkout_files - {"manifest-sha256.json"})
        for name, expected in manifest.items():
            self.assertEqual(hashlib.sha256((ROOT / name).read_bytes()).hexdigest(), expected, name)

    def test_manifest_verifier_passes_for_current_checkout(self):
        result = subprocess.run(
            [sys.executable, str(ROOT / "renderer" / "verify_manifest.py")],
            cwd=ROOT, capture_output=True, text=True,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn('"pass": true', result.stdout)

    def test_approved_benchmark_job_still_validates(self):
        result = kit.validate(
            kit.read(ROOT / "examples" / "benchmark15" / "job.json"),
            ROOT / "examples" / "benchmark15",
            approved=True,
        )
        self.assertTrue(result["valid"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
