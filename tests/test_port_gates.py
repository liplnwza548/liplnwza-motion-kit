"""Regression tests for the P0/P1 gates ported from the Kurt job.

Uses synthetic fixtures only (no Kurt audio, images, or voice data).
Run: python3 -m unittest tests.test_port_gates -v
"""
import json
import math
import subprocess
import sys
import tempfile
import unittest
import wave
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "renderer"))

import dedup_visemes  # noqa: E402
import mfa_to_cues  # noqa: E402


def run(cmd, **kw):
    return subprocess.run(cmd, capture_output=True, text=True, **kw)


def make_wav(path, seconds=2.0, rate=48000):
    import struct
    n = int(seconds * rate)
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(struct.pack("<h", 0) * n)


def make_png(path, size, color):
    from PIL import Image
    Image.new("RGB", size, color).save(path)


class PortGatesTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="port_gates_")
        self.tmp = Path(self.temp.name)

    def tearDown(self):
        self.temp.cleanup()

    def test_dedup_last_shape_wins_and_sorted(self):
        vis = [{"start": 0.5, "shape": "AA"}, {"start": 0.0, "shape": "CLOSED"},
               {"start": 0.5, "shape": "EE"}]
        out = dedup_visemes.dedupe(vis)
        self.assertEqual(out, [{"start": 0.0, "shape": "CLOSED"},
                               {"start": 0.5, "shape": "EE"}])

    def test_mfa_to_cues_merges_and_reports(self):
        script = self.tmp / "script.txt"
        script.write_text("สวัสดีชาวโลก", encoding="utf-8")
        # newmm on "สวัสดีชาวโลก" segments as ["สวัสดี", "ชาว", "โลก"];
        # merge the last two into one chip to exercise the merge path.
        merge_map = self.tmp / "merge_map.json"
        merge_map.write_text(json.dumps(
            {"newmm_merges": [{"parts": ["ชาว", "โลก"], "chip": "ชาวโลก"}]},
            ensure_ascii=False), encoding="utf-8")
        # pythainlp is not guaranteed on the test machine; the cache path
        # is the documented fallback and its concatenation is verified.
        tokens_cache = self.tmp / "tokens.json"
        tokens_cache.write_text(json.dumps(
            {"tokens": ["สวัสดี", "ชาว", "โลก"]}, ensure_ascii=False),
            encoding="utf-8")
        mfa = self.tmp / "mfa.json"
        mfa.write_text(json.dumps({"tiers": {"words": {"entries": [
            [0.0, 0.5, "สวัสดี"], [0.5, 1.0, "ชาว"], [1.0, 1.5, "โลก"],
        ]}}}), encoding="utf-8")
        out_words = self.tmp / "words.json"
        out_prov = self.tmp / "words.provenance.json"
        rc = mfa_to_cues.main(["--mfa-out", str(mfa), "--script", str(script),
                               "--merge-map", str(merge_map),
                               "--tokens-cache", str(tokens_cache),
                               "--out-words", str(out_words),
                               "--out-provenance", str(out_prov)])
        self.assertIsNone(rc)  # main() returns None on success
        words = json.loads(out_words.read_text(encoding="utf-8"))
        self.assertEqual([w["word"] for w in words], ["สวัสดี", "ชาวโลก"])
        self.assertEqual(words[1]["start"], 0.5)
        prov = json.loads(out_prov.read_text(encoding="utf-8"))
        self.assertEqual(prov["chips"], 2)
        self.assertEqual(len(prov["newmm_merges"]), 1)

    def test_mfa_to_cues_fails_on_overshoot(self):
        script = self.tmp / "script.txt"
        script.write_text("กข", encoding="utf-8")
        mfa = self.tmp / "mfa.json"
        mfa.write_text(json.dumps({"tiers": {"words": {"entries": [
            [0.0, 0.5, "กง"], [0.5, 1.0, "ข"],
        ]}}}), encoding="utf-8")
        with self.assertRaises(SystemExit):
            mfa_to_cues.main(["--mfa-out", str(mfa), "--script", str(script),
                              "--out-words", str(self.tmp / "w.json"),
                              "--out-provenance", str(self.tmp / "p.json")])

    def _preflight_job(self, voice_sha=None, off=None, off_locked=None):
        job = self.tmp / "job"
        job.mkdir(exist_ok=True)
        make_wav(job / "voice.wav", seconds=2.0)
        (job / "script.txt").write_text("สวัสดี", encoding="utf-8")
        words = [{"word": "สวัสดี", "start": 0.0, "end": 1.5}]
        (job / "words.json").write_text(json.dumps(words, ensure_ascii=False), encoding="utf-8")
        (job / "visemes.json").write_text(json.dumps(
            [{"start": 0.0, "shape": "CLOSED"}, {"start": 0.5, "shape": "AA"}]), encoding="utf-8")
        (job / "images").mkdir(exist_ok=True)
        import hashlib
        img = job / "images" / "B01.webp"
        make_png(img, (1200, 900), (255, 0, 0))
        manifest = {"beats": {"B01": {"file": "images/B01.webp",
                                      "sha256": hashlib.sha256(img.read_bytes()).hexdigest(),
                                      "status": "accepted"}},
                    "rejected": []}
        (job / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
        beats = {"beats": [{"name": "B01", "start": 0.0, "end": 2.0}], "onsets": [0.0]}
        (job / "beats.json").write_text(json.dumps(beats), encoding="utf-8")
        cmd = [sys.executable, str(ROOT / "renderer" / "preflight.py"),
               "--root", str(job), "--voice", "voice.wav", "--script", "script.txt",
               "--words", "words.json", "--visemes", "visemes.json",
               "--manifest", "manifest.json", "--beats", "beats.json",
               "--images-dir", str(job / "images"), "--planned-end", "2.0"]
        if voice_sha:
            cmd += ["--voice-sha", voice_sha]
        if off is not None:
            cmd += ["--off", str(off)]
        if off_locked is not None:
            cmd += ["--off-locked", str(off_locked)]
        return run(cmd)

    def test_preflight_passes_and_guard_fails(self):
        ok = self._preflight_job()
        self.assertEqual(ok.returncode, 0, ok.stdout + ok.stderr)
        bad_sha = self._preflight_job(voice_sha="0" * 64)
        self.assertNotEqual(bad_sha.returncode, 0)
        self.assertIn("voice_sha_locked", bad_sha.stdout)
        bad_off = self._preflight_job(off=0.08, off_locked=0.0)
        self.assertNotEqual(bad_off.returncode, 0)
        self.assertIn("off_unchanged_guard", bad_off.stdout)

    def test_verify_manifest_job_mode(self):
        job = self.tmp / "job"
        job.mkdir()
        (job / "images").mkdir()
        import hashlib
        img = job / "images" / "B01.webp"
        make_png(img, (1200, 900), (0, 255, 0))
        manifest = {"beats": {"B01": {"file": "images/B01.webp",
                                      "sha256": hashlib.sha256(img.read_bytes()).hexdigest(),
                                      "status": "accepted"}},
                    "rejected": [{"file": "images/rejected/B01-old.webp"}]}
        (job / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
        ok = run([sys.executable, str(ROOT / "renderer" / "verify_manifest.py"),
                  "--job-manifest", str(job / "manifest.json"),
                  "--job-root", str(job), "--images-dir", str(job / "images")])
        self.assertEqual(ok.returncode, 0, ok.stdout + ok.stderr)
        # A rejected file straying into the images dir must fail.
        make_png(job / "images" / "B01-old.webp", (1200, 900), (0, 0, 255))
        bad = run([sys.executable, str(ROOT / "renderer" / "verify_manifest.py"),
                   "--job-manifest", str(job / "manifest.json"),
                   "--job-root", str(job), "--images-dir", str(job / "images")])
        self.assertNotEqual(bad.returncode, 0)
        self.assertIn("rejected", bad.stdout)

    def _two_beat_video(self):
        from PIL import Image
        frames_dir = self.tmp / "frames"
        frames_dir.mkdir()
        for i in range(60):
            color = (255, 0, 0) if i < 30 else (0, 0, 255)
            Image.new("RGB", (1080, 1920), color).save(frames_dir / f"f{i:03d}.png")
        video = self.tmp / "clip.mp4"
        run(["ffmpeg", "-y", "-v", "error", "-framerate", "30", "-i",
             str(frames_dir / "f%03d.png"), "-c:v", "libx264", "-pix_fmt", "yuv420p",
             "-r", "30", str(video)], check=True)
        return video

    def test_qc_frame_index_cuts(self):
        video = self._two_beat_video()
        job = self.tmp / "job"
        job.mkdir()
        (job / "images").mkdir()
        make_png(job / "images" / "red.png", (984, 784), (255, 0, 0))
        make_png(job / "images" / "blue.png", (984, 784), (0, 0, 255))
        manifest = {"beats": {
            "B01": {"file": "images/red.png", "status": "accepted"},
            "B02": {"file": "images/blue.png", "status": "accepted"}}}
        (job / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
        beats = {"beats": [{"name": "B01", "start": 0.0, "end": 1.0, "image": "B01"},
                           {"name": "B02", "start": 1.0, "end": 2.0, "image": "B02"}]}
        (job / "beats.json").write_text(json.dumps(beats), encoding="utf-8")
        result = run([sys.executable, str(ROOT / "tests" / "qc.py"),
                      "--video", str(video), "--beats", str(job / "beats.json"),
                      "--manifest", str(job / "manifest.json"), "--root", str(job),
                      "--duration", "2", "--frames", "60",
                      "--panel-box", "0,0,1080,1920", "--img-box", "0,0,984,784"])
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("QC PASSED", result.stdout)


if __name__ == "__main__":
    unittest.main()
