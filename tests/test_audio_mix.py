"""BGM rights, stem preparation, ducking, fades, and final loudness checks."""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
import wave
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "renderer"))
import audio_mix


def write_tone(path: Path, frequency: int, seconds: float, amplitude: float = 0.04) -> None:
    rate = 48000
    signal = np.round(amplitude * 32767 * np.sin(2 * np.pi * frequency * np.arange(round(rate * seconds)) / rate)).astype("<i2")
    with wave.open(str(path), "wb") as out:
        out.setparams((1, 2, rate, 0, "NONE", "not compressed"))
        out.writeframes(signal.tobytes())


def measured_loudness(path: Path) -> dict:
    result = subprocess.run([
        "ffmpeg", "-hide_banner", "-i", str(path), "-af",
        "loudnorm=I=-16:TP=-1:LRA=7:print_format=json", "-f", "null", "-",
    ], check=True, capture_output=True, text=True)
    start = result.stderr.rfind("{")
    return json.loads(result.stderr[start:result.stderr.rfind("}") + 1])


class AudioMixTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="_audio_mix_test_", dir=ROOT / "tests")
        self.job_dir = Path(self.temp.name)
        (self.job_dir / "inputs").mkdir()
        write_tone(self.job_dir / "inputs" / "synthetic-bed.wav", 220, 4.2)

    def tearDown(self):
        self.temp.cleanup()

    def approved_test_job(self):
        return {
            "duration": 4.0,
            "sources": [{
                "id": "synthetic-bed", "origin": "generated synthetic test waveform",
                "creator": "test fixture", "license": "synthetic signal; test only",
                "usage": "TEST ONLY; not a music asset", "checked_date": "2026-10-25",
                "rights": {"status": "cleared", "evidence": "Generated in test from a sine oscillator", "checked_date": "2026-10-25"},
                "approval": {"status": "approved", "approved_by": "Philip", "evidence": "TEST FIXTURE ONLY; not production approval"},
            }],
            "bgm": {"source_id": "synthetic-bed", "path": "inputs/synthetic-bed.wav"},
        }

    def test_no_bgm_is_optional_and_keeps_a_working_voice_sfx_graph(self):
        self.assertIsNone(audio_mix.validate_bgm({"duration": 4, "sources": []}, self.job_dir, 4))
        graph = audio_mix.build_audio_filter(4, None)
        self.assertIn("[1:a]", graph)
        self.assertIn("[2:a]", graph)
        self.assertIn("loudnorm=I=-16.0:TP=-1.0", graph)
        self.assertNotIn("[3:a]", graph)

    def test_no_bgm_filter_runs_through_ffmpeg(self):
        voice = self.job_dir / "inputs" / "voice.wav"
        sfx = self.job_dir / "inputs" / "sfx.wav"
        write_tone(voice, 440, 4, 0.08)
        with wave.open(str(sfx), "wb") as out:
            out.setparams((2, 2, 48000, 0, "NONE", "not compressed"))
            out.writeframes(np.zeros((48000 * 4, 2), dtype="<i2").tobytes())
        output = self.job_dir / "without_bgm.wav"
        subprocess.run([
            "ffmpeg", "-y", "-v", "error", "-f", "lavfi", "-i", "color=c=black:s=16x16:d=4:r=30",
            "-i", str(voice), "-i", str(sfx), "-filter_complex", audio_mix.build_audio_filter(4, None),
            "-map", "[a]", "-c:a", "pcm_s16le", str(output),
        ], check=True)
        self.assertTrue(output.is_file())

    def test_missing_source_or_rights_fails_closed(self):
        job = self.approved_test_job()
        job["sources"] = []
        with self.assertRaisesRegex(ValueError, "must resolve to exactly one source"):
            audio_mix.validate_bgm(job, self.job_dir, 4)
        job = self.approved_test_job()
        del job["sources"][0]["rights"]
        with self.assertRaisesRegex(ValueError, "rights are incomplete"):
            audio_mix.validate_bgm(job, self.job_dir, 4)
        job = self.approved_test_job()
        job["sources"][0]["approval"]["status"] = "pending"
        with self.assertRaisesRegex(ValueError, "not approved by Philip"):
            audio_mix.validate_bgm(job, self.job_dir, 4)

    def test_bgm_requires_recorded_rights_evidence_and_philip_track_approval(self):
        job = self.approved_test_job()
        job["sources"][0]["rights"]["evidence"] = "  "
        with self.assertRaisesRegex(ValueError, "rights are incomplete"):
            audio_mix.validate_bgm(job, self.job_dir, 4)
        job = self.approved_test_job()
        job["sources"][0]["approval"]["evidence"] = ""
        with self.assertRaisesRegex(ValueError, "not approved by Philip"):
            audio_mix.validate_bgm(job, self.job_dir, 4)
        job = self.approved_test_job()
        job["sources"][0]["approval"]["approved_by"] = "test fixture"
        with self.assertRaisesRegex(ValueError, "not approved by Philip"):
            audio_mix.validate_bgm(job, self.job_dir, 4)

    def test_missing_file_short_track_and_looping_fail_clearly(self):
        job = self.approved_test_job()
        job["bgm"]["path"] = "inputs/missing.wav"
        with self.assertRaisesRegex(ValueError, "missing or outside"):
            audio_mix.validate_bgm(job, self.job_dir, 4)
        job = self.approved_test_job()
        write_tone(self.job_dir / "inputs" / "short.wav", 220, 2)
        job["bgm"]["path"] = "inputs/short.wav"
        with self.assertRaisesRegex(ValueError, "shorter than the requested"):
            audio_mix.validate_bgm(job, self.job_dir, 4)
        job = self.approved_test_job()
        job["bgm"]["loop"] = True
        with self.assertRaisesRegex(ValueError, "looping is not supported"):
            audio_mix.validate_bgm(job, self.job_dir, 4)
        job = self.approved_test_job()
        job["bgm"]["fade_in_s"] = 0.25
        with self.assertRaisesRegex(ValueError, "fade_in_s is fixed at 0.5"):
            audio_mix.validate_bgm(job, self.job_dir, 4)
        job = self.approved_test_job()
        job["bgm"]["ducking"] = False
        with self.assertRaisesRegex(ValueError, "ducking cannot be disabled"):
            audio_mix.validate_bgm(job, self.job_dir, 4)

    def test_bgm_stem_and_filter_normalize_duck_fade_and_target_final_mix(self):
        job = self.approved_test_job()
        voice = self.job_dir / "inputs" / "voice.wav"
        sfx = self.job_dir / "inputs" / "sfx.wav"
        write_tone(voice, 440, 4, 0.12)
        bgm = audio_mix.validate_bgm(job, self.job_dir, 4)
        raw_bgm = audio_mix.prepare_bgm_stem(bgm, 4, self.job_dir / "output" / "bgm_pcm.wav")
        voice_norm = audio_mix.normalize_stem(voice, self.job_dir / "output" / "voice_normalized.wav", 4)
        bgm_norm = audio_mix.normalize_stem(raw_bgm, self.job_dir / "output" / "bgm_normalized.wav", 4)
        for stem in (voice_norm, bgm_norm):
            normalized = measured_loudness(stem)
            self.assertAlmostEqual(float(normalized["input_i"]), -16.0, delta=1.0)
            self.assertLessEqual(float(normalized["input_tp"]), -1.0)
        effective_gain, duck_analysis = audio_mix.safe_bgm_gain(voice_norm, bgm_norm, bgm["gain_db"])
        bgm = {**bgm, "requested_gain_db": bgm["gain_db"], "gain_db": effective_gain, "duck_analysis": duck_analysis}
        self.assertTrue(raw_bgm.is_file())
        self.assertGreaterEqual(duck_analysis["minimum_measured_voice_over_bgm_db"], 12.0)
        graph = audio_mix.build_audio_filter(4, bgm)
        self.assertIn("[1:a]", graph)
        self.assertIn("[3:a]", graph)
        self.assertIn("sidechaincompress=threshold=0.005:ratio=20:attack=20:release=250", graph)
        self.assertIn("afade=t=in:st=0:d=0.500000", graph)
        self.assertIn("afade=t=out:st=2.500000:d=1.500000", graph)
        self.assertEqual(audio_mix.mix_report(bgm)["minimum_duck_below_voice_db"], 12.0)
        with wave.open(str(sfx), "wb") as out:
            out.setparams((2, 2, 48000, 0, "NONE", "not compressed"))
            out.writeframes(np.zeros((48000 * 4, 2), dtype="<i2").tobytes())
        mixed = self.job_dir / "output" / "mixed.wav"
        subprocess.run([
            "ffmpeg", "-y", "-v", "error", "-f", "lavfi", "-i", "color=c=black:s=16x16:d=4:r=30",
            "-i", str(voice_norm), "-i", str(sfx), "-i", str(bgm_norm),
            "-filter_complex", graph, "-map", "[a]", "-c:a", "pcm_s16le", str(mixed),
        ], check=True)
        self.assertTrue(mixed.is_file())
        probe = json.loads(subprocess.check_output([
            "ffprobe", "-v", "error", "-show_format", "-of", "json", str(mixed),
        ]))
        self.assertAlmostEqual(float(probe["format"]["duration"]), 4.0, delta=0.03)
        measured = measured_loudness(mixed)
        self.assertLessEqual(float(measured["input_tp"]), -1.0)
        self.assertAlmostEqual(float(measured["input_i"]), -16.0, delta=1.0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
