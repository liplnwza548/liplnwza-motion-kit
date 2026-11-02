"""Theme contract regressions using synthetic, TEST ONLY content."""
from __future__ import annotations

import copy
import hashlib
import importlib
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
import wave
from pathlib import Path
from unittest.mock import patch

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "renderer"))
import kit

try:
    import theme_config
except ImportError:
    theme_config = None

try:
    import theme_assets
except ImportError:
    theme_assets = None

TEST_JOB = ROOT / "jobs" / "theme-runtime-test-01" / "job.json"
LEGACY_FRAME = ROOT / "jobs" / "theme-runtime-test-01" / "output-test-v01" / "baseline-t0.000.png"
POSES = ("explain", "point_right", "thinking", "magnify", "point_left", "thumbs_up")


def base_theme(theme_id: str = "base-paper", version: str = "v001") -> dict:
    """Literal v0.2.1 values, independently recorded before theme wiring."""
    return {
        "schema_version": 1,
        "id": theme_id,
        "version": version,
        "layout_profile": "paper-v021",
        "font": {"id": "prompt-bold", "version": "v001"},
        "palette": {
            "ink": "#181B26",
            "paper": "#FFFDF6",
            "accents": ["#FFD648", "#2264D8", "#F44336", "#38B577"],
        },
        "text_colors": {
            "paper": "#181B26",
            "accents": ["#181B26", "#FFFDF6", "#FFFDF6", "#FFFDF6"],
        },
        "background": {
            "mode": "grid",
            "colors": ["#F3DFDC", "#D7E9DB", "#DCE6F5", "#F4E9CE"],
            "asset": None,
            "grid": {
                "enabled": True,
                "step_px": 52,
                "color": "#785F5A",
                "opacity": 40 / 255,
                "width_px": 2,
            },
        },
        "cards": {
            "style": "rough-paper",
            "border_px": 4,
            "outline_px": 11,
            "shadow_offset_px": [6, 6],
            "roughness_px": 5,
            "padding_px": 9,
        },
        "captions": {
            "preset": "base-paper-v001",
            "font_size_px": 80,
            "height_px": 140,
            "y_px": 1635,
            "gap_px": 18,
            "max_width_px": 960,
            "padding_px": 16,
            "fill_palette_indexes": [0, 1, 2, 3],
            "text_palette_keys": ["ink", "paper", "paper", "paper"],
        },
        "layout": {
            "brand_center_px": [228, 92],
            "topic_center_px": [850, 92],
            "title_center_px": [540, 255],
            "content_center_px": [540, 555],
            "mascot_center_px": [375, 1210],
            "mascot_right_center_px": [710, 1210],
            "aside_center_px": [820, 1130],
            "aside_right_center_px": [265, 1130],
            "cta_center_px": [540, 1465],
            "footer_box": [75, 1765, 930, 64],
            "progress_box": [90, 1850, 990, 1860],
        },
        "motion": {"seed": 90, "mascot_bob_px": 7, "mascot_bob_rate": 3.0},
        "audio": {"bgm_default": "off", "sfx_gain": 1.0},
    }


def write_asset(root: Path, asset_id: str, version: str = "v001", *,
                status: str = "approved", category: str = "backgrounds", relative_path: str = "background.png",
                data: bytes | None = None) -> Path:
    asset_dir = root / "library" / category / asset_id / version
    asset_dir.mkdir(parents=True, exist_ok=True)
    if data is None:
        image = Image.new("RGBA", (2, 2), (80, 40, 120, 255))
        from io import BytesIO
        buf = BytesIO()
        image.save(buf, format="PNG")
        data = buf.getvalue()
    file_path = asset_dir / relative_path
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_bytes(data)
    metadata_path = asset_dir / "asset.json"
    metadata_path.write_text(json.dumps({
        "schema_version": 1,
        "id": asset_id,
        "category": category,
        "version": version,
        "status": status,
        "primary_file": relative_path,
        "files": [{
            "path": relative_path,
            "sha256": hashlib.sha256(data).hexdigest(),
            "mime": "image/png",
        }],
        "approval": {
            "approved_by": "Philip" if status == "approved" else None,
            "evidence": "TEST FIXTURE ONLY; no production asset approval",
        },
    }, indent=2) + "\n", encoding="utf-8")
    index_path = root / "library" / "index.json"
    index_path.parent.mkdir(parents=True, exist_ok=True)
    entries = []
    if index_path.exists():
        entries = json.loads(index_path.read_text(encoding="utf-8")).get("assets", [])
    entries = [e for e in entries if not (e.get("id") == asset_id and e.get("version") == version)]
    entries.append({
        "id": asset_id,
        "category": category,
        "version": version,
        "status": status,
        "metadata": f"library/{category}/{asset_id}/{version}/asset.json",
    })
    index_path.write_text(json.dumps({"schema_version": 1, "assets": entries}, indent=2) + "\n", encoding="utf-8")
    return file_path


def write_test_kit(root: Path, themes: list[dict] | None = None, *, with_asset: bool = False) -> Path:
    (root / "renderer").mkdir(parents=True, exist_ok=True)
    (root / "themes").mkdir(parents=True, exist_ok=True)
    (root / "assets" / "fonts").mkdir(parents=True, exist_ok=True)
    rig = root / "assets" / "mascot" / "mouth_rig"
    for sub in ("original", "clean"):
        (rig / sub).mkdir(parents=True, exist_ok=True)
        for pose in POSES:
            (rig / sub / f"{pose}.png").write_bytes(f"TEST-{sub}-{pose}".encode())
    (rig / "rig_motion.py").write_text("# TEST fixture renderer identity\n", encoding="utf-8")
    (rig / "profiles.json").write_text("{}\n", encoding="utf-8")
    for filename in ("kit.py", "theme_config.py", "theme_assets.py"):
        (root / "renderer" / filename).write_text(f"# TEST fixture: {filename}\n", encoding="utf-8")
    (root / "themes" / "theme.schema.json").write_text('{"schema_version":1}\n', encoding="utf-8")
    (root / "assets" / "fonts" / "Prompt-Bold.ttf").write_bytes(b"TEST FONT v1")
    index_themes = []
    for config in themes or [base_theme()]:
        theme_path = root / "themes" / config["id"] / config["version"] / "theme.json"
        theme_path.parent.mkdir(parents=True, exist_ok=True)
        theme_path.write_text(json.dumps(config, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        index_themes.append({"id": config["id"], "version": config["version"], "status": "approved"})
    (root / "themes" / "index.json").write_text(json.dumps({"schema_version": 1, "themes": index_themes}, indent=2) + "\n", encoding="utf-8")
    if not (root / "library" / "index.json").exists():
        (root / "library").mkdir(parents=True, exist_ok=True)
        (root / "library" / "index.json").write_text('{"schema_version":1,"assets":[]}\n', encoding="utf-8")
    if with_asset:
        write_asset(root, "test-background")
    return root


def make_test_job(job_dir: Path, *, theme: dict | None = None, bgm: bool = False) -> Path:
    (job_dir / "inputs").mkdir(parents=True, exist_ok=True)
    rate, duration = 48000, 12
    t = np.arange(rate * duration, dtype=np.float64) / rate
    signal = np.round(0.02 * 32767 * np.sin(2 * np.pi * 440 * t)).astype("<i2")
    with wave.open(str(job_dir / "inputs" / "test-tone.wav"), "wb") as out:
        out.setparams((1, 2, rate, 0, "NONE", "not compressed"))
        out.writeframes(signal.tobytes())
    words = [{"word": "TEST", "start": 0.2, "end": 0.8}, {"word": "ONLY", "start": 1.0, "end": 1.6}]
    visemes = [{"start": 0.0, "shape": "AA"}, {"start": 1.0, "shape": "CLOSED"}]
    (job_dir / "words.json").write_text(json.dumps(words, indent=2) + "\n", encoding="utf-8")
    (job_dir / "visemes.json").write_text(json.dumps(visemes, indent=2) + "\n", encoding="utf-8")
    test_sources = []
    job = {
        "schema_version": 1,
        "title": "TEST ONLY: theme runtime",
        "topic_label": "TEST ONLY",
        "duration": duration,
        "voice": "inputs/test-tone.wav",
        "words": "words.json",
        "visemes": "visemes.json",
        "footer": "TEST ONLY - NOT A CLIP",
        "sources": test_sources,
        "scenes": [{"start": 0, "end": duration, "layout": "title", "title": "TEST ONLY", "body": "SYNTHETIC CHECK", "pose": "explain"}],
    }
    if theme is not None:
        job["theme"] = copy.deepcopy(theme)
    if bgm:
        def write_test_bed(path: Path, frequency: int) -> None:
            bed = np.round(0.03 * 32767 * np.sin(2 * np.pi * frequency * t)).astype("<i2")
            with wave.open(str(path), "wb") as out:
                out.setparams((1, 2, rate, 0, "NONE", "not compressed"))
                out.writeframes(bed.tobytes())
        write_test_bed(job_dir / "inputs" / "test-bed.wav", 220)
        job["bgm"] = {"source_id": "test-bed", "path": "inputs/test-bed.wav"}
        job["sources"].append({
            "id": "test-bed", "origin": "synthetic test signal", "creator": "test fixture",
            "license": "synthetic; test use only", "usage": "TEST ONLY; never a production music source",
            "checked_date": "2026-10-25",
            "rights": {"status": "cleared", "evidence": "Synthetic oscillator generated by this test", "checked_date": "2026-10-25"},
            "approval": {"status": "approved", "approved_by": "Philip", "evidence": "TEST FIXTURE ONLY; not production approval"},
        })
    job_path = job_dir / "job.json"
    job_path.write_text(json.dumps(job, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (job_dir / "approval.json").write_text(json.dumps({"status": "pending", "job_digest": None, "evidence": None}, indent=2) + "\n", encoding="utf-8")
    return job_path


class ThemeRuntimeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="_theme_runtime_test_", dir=ROOT / "tests")
        self.temp_root = Path(self.temp.name)

    def tearDown(self):
        self.temp.cleanup()

    def require_theme_config(self):
        self.assertIsNotNone(theme_config, "renderer/theme_config.py must provide load_theme")
        return theme_config

    def require_theme_assets(self):
        self.assertIsNotNone(theme_assets, "renderer/theme_assets.py must provide resolve_asset")
        return theme_assets

    def make_batch2_job(self, name: str = "batch2"):
        job_dir = self.temp_root / name
        job_dir.mkdir()
        job_path = make_test_job(job_dir)
        job = kit.read(job_path)
        job["render_policy_version"] = 1
        return job_path, job, job_dir

    def test_no_theme_resolves_the_pinned_legacy_base_paper(self):
        module = self.require_theme_config()
        resolved = module.load_theme(ROOT, None)
        self.assertEqual((resolved["id"], resolved["version"]), ("base-paper", "v001"))
        self.assertEqual(resolved["palette"]["ink"], "#181B26")
        self.assertEqual(resolved["palette"]["accents"], ["#FFD648", "#2264D8", "#F44336", "#38B577"])
        self.assertEqual(resolved["background"]["grid"]["step_px"], 52)
        self.assertEqual(resolved["cards"]["outline_px"], 11)
        self.assertEqual(resolved["layout"]["progress_box"], [90, 1850, 990, 1860])
        self.assertTrue(Path(resolved["font"]["path"]).is_file())

    @unittest.skipUnless(
        (ROOT / "library" / "index.json").is_file(),
        "Halloween art library is absent from this checkout while asset rights are pending; "
        "asset resolution remains covered by synthetic fixtures.",
    )
    def test_halloween_draft_theme_and_assets_resolve_only_in_explicit_review_mode(self):
        config_module = self.require_theme_config()
        asset_module = self.require_theme_assets()
        selection = {"id": "halloween", "version": "v001"}
        with self.assertRaisesRegex(ValueError, "not approved"):
            config_module.load_theme(ROOT, selection)
        with self.assertRaisesRegex(ValueError, "not approved"):
            asset_module.resolve_asset(ROOT, "moon-mist", "v001")

        resolved = config_module.load_theme(ROOT, selection, allow_draft=True)
        self.assertEqual((resolved["id"], resolved["version"]), ("halloween", "v001"))
        resolved_by_id = {asset["id"]: asset for asset in resolved["_resolved_assets"]}
        self.assertEqual(
            {asset_id: asset["status"] for asset_id, asset in resolved_by_id.items()},
            {
                "pumpkin-paper": "draft",
                "moon-mist": "draft",
                "pumpkin-smile": "draft",
                "bat-sticker": "draft",
                "constellation-sticker": "draft",
                "halloween-capsule": "draft",
                "liplnwza-halloween-costume": "approved",
            },
        )
        self.assertEqual(
            resolved_by_id["liplnwza-halloween-costume"]["sha256"],
            "1d3574d00d3d09d8099a1c1f868cf13cff133f92a547e7eb4f3d43fbd191414f",
        )
        asset_ids = {asset["id"] for asset in resolved["_resolved_assets"]}
        self.assertEqual(asset_ids, {
            "pumpkin-paper", "moon-mist", "pumpkin-smile", "bat-sticker",
            "constellation-sticker", "halloween-capsule", "liplnwza-halloween-costume",
        })
        self.assertEqual(len(resolved["_resolved_assets"]), 7, "the default background and its required variant slot resolve once")
        self.assertEqual(resolved["captions"]["resolved_preset"]["border"]["width_px"], 4)
        self.assertEqual(resolved["captions"]["resolved_preset"]["font"]["id"], "prompt-bold")
        self.assertNotIn("timing_policy", resolved["captions"]["resolved_preset"])
        self.assertTrue(all(decoration["collision_policy"] == "skip" for decoration in resolved["decorations"]))
        self.assertTrue(all(decoration["motion"] == "static" for decoration in resolved["decorations"]))

        dependencies = set(kit.theme_dependencies(resolved))
        for asset in resolved["_resolved_assets"]:
            self.assertIn(Path(asset["path"]).resolve(), dependencies)
            self.assertIn(Path(asset["metadata_path"]).resolve(), dependencies)

    def test_draft_review_mode_still_rejects_invalid_theme_fields(self):
        module = self.require_theme_config()
        config = base_theme("review-theme")
        root = write_test_kit(self.temp_root / "draft-validation", [config])
        index_path = root / "themes" / "index.json"
        index = json.loads(index_path.read_text(encoding="utf-8"))
        index["themes"][0]["status"] = "draft"
        index_path.write_text(json.dumps(index), encoding="utf-8")
        theme_path = root / "themes" / "review-theme" / "v001" / "theme.json"
        config = json.loads(theme_path.read_text(encoding="utf-8"))
        config["unreviewed_field"] = True
        theme_path.write_text(json.dumps(config), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "Unsupported theme fields"):
            module.load_theme(root, {"id": "review-theme", "version": "v001"}, allow_draft=True)

    def test_theme_can_pin_deterministic_drift_for_safe_area_checked_decorations(self):
        module = self.require_theme_config()
        config = base_theme("drift-theme")
        config["decorations"] = [{
            "id": "drift-deco", "asset": {"id": "drift-deco", "version": "v001"},
            "center_px": [880, 1260], "size_px": 46,
            "intended_use": "TEST ONLY empty corner", "safe_area_blocks": [
                "mascot_face", "mascot_mouth", "evidence", "logo", "numbers", "caption_chips", "text_safe_area",
            ], "collision_policy": "skip", "motion": "drift",
        }]
        root = write_test_kit(self.temp_root / "drift-theme", [config])
        write_asset(root, "drift-deco", category="decorations")
        resolved = module.load_theme(root, {"id": "drift-theme", "version": "v001"})
        self.assertEqual(resolved["decorations"][0]["motion"], "drift")

        job_dir = self.temp_root / "drift-job"
        job_dir.mkdir()
        job_path = make_test_job(job_dir, theme={"id": "drift-theme", "version": "v001"})
        job = kit.read(job_path)
        job["render_policy_version"] = 1
        job_path.write_text(json.dumps(job, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        with patch.object(kit, "ROOT", root):
            first = kit.Composition(job_path, self.temp_root / "drift-output-a")
            repeat = kit.Composition(job_path, self.temp_root / "drift-output-b")
            frame_t0 = np.asarray(first.frame(0.0), dtype=np.uint8)
            repeated_t0 = np.asarray(repeat.frame(0.0), dtype=np.uint8)
            frame_t1 = np.asarray(first.frame(1.0), dtype=np.uint8)
        self.assertTrue(np.array_equal(frame_t0, repeated_t0), "same seed and time must reproduce the same decoration frame")
        self.assertFalse(np.array_equal(frame_t0[1180:1320, 810:950], frame_t1[1180:1320, 810:950]),
                         "drift-enabled decoration must move deterministically within its safe corner")

    def test_missing_pending_and_wrong_theme_versions_fail_closed(self):
        module = self.require_theme_config()
        with self.assertRaises(ValueError):
            module.load_theme(ROOT, {"id": "theme-does-not-exist", "version": "v001"})
        with self.assertRaises(ValueError):
            module.load_theme(ROOT, {"id": "base-paper", "version": "v999"})
        pending_root = write_test_kit(self.temp_root / "pending", [base_theme("pending-theme")])
        index_path = pending_root / "themes" / "index.json"
        index = json.loads(index_path.read_text(encoding="utf-8"))
        index["themes"][0]["status"] = "pending"
        index_path.write_text(json.dumps(index), encoding="utf-8")
        with self.assertRaises(ValueError):
            module.load_theme(pending_root, {"id": "pending-theme", "version": "v001"})
        with self.assertRaises(ValueError):
            module.load_theme(pending_root, {"id": "pending-theme", "version": "v001"}, allow_draft=True)

    def test_resolve_asset_requires_approved_exact_version_safe_path_and_hash(self):
        module = self.require_theme_assets()
        root = write_test_kit(self.temp_root / "assets")
        with self.assertRaises(ValueError):
            module.resolve_asset(root, "missing-id", "v001")

        write_asset(root, "draft-image", status="draft")
        with self.assertRaises(ValueError):
            module.resolve_asset(root, "draft-image", "v001")

        write_asset(root, "exact-image", version="v001")
        with self.assertRaises(ValueError):
            module.resolve_asset(root, "exact-image", "v002")

        write_asset(root, "path-escape", relative_path="../../../../outside.png")
        with self.assertRaises(ValueError):
            module.resolve_asset(root, "path-escape", "v001")

        write_asset(root, "executable", relative_path="run.py", data=b"print('TEST')")
        with self.assertRaises(ValueError):
            module.resolve_asset(root, "executable", "v001")

        path = write_asset(root, "tampered")
        path.write_bytes(path.read_bytes() + b"tamper")
        with self.assertRaises(ValueError):
            module.resolve_asset(root, "tampered", "v001")

    def test_digest_changes_for_theme_png_font_bgm_and_renderer_identity(self):
        for changed in ("theme", "png", "font", "bgm", "renderer"):
            with self.subTest(changed=changed):
                root = self.temp_root / changed
                config = base_theme("test-paper")
                config["background"] = {"mode": "image", "colors": ["#F3DFDC"], "asset": {"id": "test-background", "version": "v001"}, "grid": {"enabled": False, "step_px": 52, "color": "#785F5A", "opacity": 0, "width_px": 2}}
                write_test_kit(root, [config], with_asset=True)
                job_dir = self.temp_root / f"job-{changed}"
                job_dir.mkdir()
                job_path = make_test_job(job_dir, theme={"id": "test-paper", "version": "v001"}, bgm=True)
                job = kit.read(job_path)
                rig_root = root / "assets" / "mascot" / "mouth_rig"
                with patch.object(kit, "ROOT", root), patch.object(kit, "MOUTH_RIG_ROOT", rig_root):
                    before = kit.digest(job, job_dir)
                    if changed == "theme":
                        theme_path = root / "themes" / "test-paper" / "v001" / "theme.json"
                        config = json.loads(theme_path.read_text(encoding="utf-8"))
                        config["palette"]["ink"] = "#101010"
                        theme_path.write_text(json.dumps(config), encoding="utf-8")
                    elif changed == "png":
                        png_path = root / "library" / "backgrounds" / "test-background" / "v001" / "background.png"
                        png_path.write_bytes(png_path.read_bytes() + b"new approved bytes")
                        metadata_path = png_path.parent / "asset.json"
                        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
                        metadata["files"][0]["sha256"] = hashlib.sha256(png_path.read_bytes()).hexdigest()
                        metadata_path.write_text(json.dumps(metadata), encoding="utf-8")
                    elif changed == "font":
                        (root / "assets" / "fonts" / "Prompt-Bold.ttf").write_bytes(b"TEST FONT v2")
                    elif changed == "bgm":
                        bed = np.round(0.03 * 32767 * np.sin(2 * np.pi * 330 * np.arange(48000 * 12) / 48000)).astype("<i2")
                        with wave.open(str(job_dir / "inputs" / "test-bed.wav"), "wb") as out:
                            out.setparams((1, 2, 48000, 0, "NONE", "not compressed"))
                            out.writeframes(bed.tobytes())
                    else:
                        (root / "renderer" / "kit.py").write_text("# TEST fixture renderer identity v2\n", encoding="utf-8")
                    after = kit.digest(job, job_dir)
                self.assertNotEqual(before, after)

    def test_two_loaded_themes_keep_distinct_backgrounds_in_one_process(self):
        module = self.require_theme_config()
        first = base_theme("test-paper-a")
        second = base_theme("test-paper-b")
        second["background"]["colors"] = ["#111820"]
        root = write_test_kit(self.temp_root / "two-themes", [first, second])
        job_a_dir = self.temp_root / "job-a"
        job_b_dir = self.temp_root / "job-b"
        job_a_dir.mkdir()
        job_b_dir.mkdir()
        job_a = make_test_job(job_a_dir, theme={"id": "test-paper-a", "version": "v001"})
        job_b = make_test_job(job_b_dir, theme={"id": "test-paper-b", "version": "v001"})
        with patch.object(kit, "ROOT", root):
            a = kit.Composition(job_a, self.temp_root / "out-a")
            before = a.frame(0.2).getpixel((40, 40))
            theme_a_path = root / "themes" / "test-paper-a" / "v001" / "theme.json"
            changed_on_disk = json.loads(theme_a_path.read_text(encoding="utf-8"))
            changed_on_disk["background"]["colors"] = ["#ABCDEF"]
            theme_a_path.write_text(json.dumps(changed_on_disk), encoding="utf-8")
            still_pinned = a.frame(0.2).getpixel((40, 40))
            b = kit.Composition(job_b, self.temp_root / "out-b")
            other_theme = b.frame(0.2).getpixel((40, 40))
        self.assertEqual(before, (243, 223, 220))
        self.assertEqual(still_pinned, before)
        self.assertEqual(other_theme, (17, 24, 32))
        self.assertNotEqual(before, other_theme)

    def test_base_theme_frame_matches_legacy_outside_the_fixed_progress_start(self):
        self.assertTrue(LEGACY_FRAME.is_file(), "pre-theme t=0 TEST frame must be kept as a comparison fixture")
        comp = kit.Composition(TEST_JOB, self.temp_root / "base-paper-output")
        current = np.asarray(comp.frame(0), dtype=np.uint8)
        legacy = np.asarray(Image.open(LEGACY_FRAME).convert("RGB"), dtype=np.uint8)
        pixel_delta = np.max(np.abs(current.astype(np.int16) - legacy.astype(np.int16)), axis=2)
        changed = pixel_delta > 0
        changed[1840:1870, 80:120] = False
        text_antialias_zones = ((160, 65, 332, 125), (385, 1775, 685, 1812))
        for x0, y0, x1, y1 in text_antialias_zones:
            self.assertLessEqual(
                int(pixel_delta[y0:y1, x0:x1].max()), 5,
                "legacy text may differ only by tiny rasterization antialiasing",
            )
            changed[y0:y1, x0:x1] = False
        self.assertEqual(int(changed.sum()), 0, "base-paper must preserve legacy colors, grid, cards, and layout")

    def test_progress_bar_is_empty_at_zero_and_grows_over_the_first_frames(self):
        comp = kit.Composition(TEST_JOB, self.temp_root / "progress-output")
        ink = np.array([24, 27, 38], dtype=np.uint8)

        def filled_pixels(t):
            frame = np.asarray(comp.frame(t), dtype=np.uint8)
            region = frame[1850:1860, 90:120]
            return int(np.all(region == ink, axis=2).sum())

        at_zero = filled_pixels(0)
        at_two_frames = filled_pixels(2 / kit.FPS)
        at_four_frames = filled_pixels(4 / kit.FPS)
        self.assertEqual(at_zero, 0, "zero progress must not draw a black capsule")
        self.assertGreater(at_two_frames, at_zero)
        self.assertGreater(at_four_frames, at_two_frames)

    def test_v2_approved_render_never_overwrites_an_existing_output(self):
        self.require_theme_config()
        job_dir = self.temp_root / "approved-output-test"
        job_dir.mkdir()
        job_path = make_test_job(job_dir, theme={"id": "base-paper", "version": "v001"})
        job = kit.read(job_path)
        digest = kit.digest(job, job_dir)
        (job_dir / "approval.json").write_text(json.dumps({
            "status": "approved",
            "approval_digest_version": 2,
            "job_digest": digest,
            "evidence": "TEST FIXTURE ONLY; synthetic output guard test, not owner approval",
        }, indent=2) + "\n", encoding="utf-8")
        validation = kit.validate(job, job_dir, approved=True)
        self.assertEqual(validation.get("approval_digest_version"), 2)
        out = self.temp_root / "existing-output"
        out.mkdir()
        sentinel = out / "video.mp4"
        sentinel.write_bytes(b"TEST OLD OUTPUT SENTINEL")
        result = subprocess.run(
            [sys.executable, str(ROOT / "renderer" / "kit.py"), "render", str(job_path), "--out", str(out)],
            capture_output=True, text=True,
        )
        self.assertEqual(result.returncode, 2)
        self.assertIn("Output video exists", result.stderr)
        self.assertEqual(sentinel.read_bytes(), b"TEST OLD OUTPUT SENTINEL")

    def test_batch1_card_and_theme_icon_use_overshoot_pop(self):
        theme = base_theme()
        theme["_cache_key"] = "test-theme"
        theme["_render_policy_enabled"] = True
        card_scales = []
        with patch.object(kit, "layer", side_effect=lambda *args, **kwargs: card_scales.append(args[4])):
            kit.sign(
                Image.new("RGBA", (1080, 1920)), 540, 500, 500, 180, "TEST CARD",
                "#FFD648", 60, 0.32 * 0.58, 0, 1, theme, "#181B26",
            )
        self.assertEqual(len(card_scales), 1)
        self.assertEqual(kit.card_pop_scale(0.0), 0.0, "staggered cards remain hidden before their start")
        self.assertGreaterEqual(kit.card_pop_scale(0.001), 0.85)
        self.assertGreater(card_scales[0], 1.045, "the card must overshoot close to 1.05x")
        self.assertLess(card_scales[0], 1.06, "the card overshoot must stay within the safe layout margin")
        self.assertAlmostEqual(kit.card_pop_scale(0.32), 1.0)
        self.assertAlmostEqual(kit.pop(1), 1.0)

        config = base_theme("icon-theme")
        config["decorations"] = [{
            "id": "test-icon", "asset": {"id": "test-icon", "version": "v001"},
            "center_px": [900, 1320], "size_px": 44, "intended_use": "TEST safe-corner icon",
            "safe_area_blocks": ["mascot_face", "mascot_mouth", "evidence", "logo", "numbers", "caption_chips", "text_safe_area"],
            "collision_policy": "skip", "motion": "static",
        }]
        root = write_test_kit(self.temp_root / "icon-kit", [config])
        write_asset(root, "test-icon", category="decorations")
        job_dir = self.temp_root / "icon-job"
        job_dir.mkdir()
        job_path = make_test_job(job_dir, theme={"id": "icon-theme", "version": "v001"})
        job = kit.read(job_path)
        job["render_policy_version"] = 1
        kit.write(job_path, job)
        with patch.object(kit, "ROOT", root):
            composition = kit.Composition(job_path, self.temp_root / "icon-output")
            observed_icon_scales = []
            original_layer = kit.layer
            def capture_icon_scale(im, asset, cx, cy, scale=1, angle=0):
                if asset.size == (2, 2):observed_icon_scales.append(scale)
                return original_layer(im, asset, cx, cy, scale, angle)
            with patch.object(kit, "layer", side_effect=capture_icon_scale):
                composition.frame(0.1)
        self.assertEqual(len(observed_icon_scales), 1)
        self.assertAlmostEqual(observed_icon_scales[0], kit.card_pop_scale(0.1), places=6)

    def test_batch1_summary_items_stagger(self):
        job_dir = self.temp_root / "summary-stagger"
        job_dir.mkdir()
        job_path = make_test_job(job_dir)
        job = kit.read(job_path)
        job["render_policy_version"] = 1
        job["scenes"] = [{
            "start": 0, "end": 12, "layout": "summary", "title": "SUMMARY",
            "body": "TAKEAWAY", "items": ["FIRST", "SECOND", "THIRD"], "pose": "explain",
        }]
        kit.write(job_path, job)
        composition = kit.Composition(job_path, self.temp_root / "summary-stagger-output")
        with patch.object(kit, "sign", wraps=kit.sign) as sign_spy:
            composition.frame(0.25)
        item_ages = {
            call.args[5]: call.args[8]
            for call in sign_spy.call_args_list
            if len(call.args) > 8 and call.args[5] in {"FIRST", "SECOND", "THIRD"}
        }
        self.assertEqual(set(item_ages), {"FIRST", "SECOND", "THIRD"})
        self.assertGreater(item_ages["FIRST"], 0)
        self.assertLessEqual(item_ages["SECOND"], 0)
        self.assertLessEqual(item_ages["THIRD"], item_ages["SECOND"])

    def test_batch1_scene_background_variants_change_midclip(self):
        from io import BytesIO

        config = base_theme("variant-theme")
        config["background"] = {
            **config["background"], "mode": "image",
            "asset": {"id": "paper-light", "version": "v001"},
        }
        config["background_variants"] = [
            {"id": "light", "asset": {"id": "paper-light", "version": "v001"}, "intended_use": "TEST light scene"},
            {"id": "dark", "asset": {"id": "paper-dark", "version": "v001"}, "intended_use": "TEST dark scene"},
        ]
        root = write_test_kit(self.temp_root / "variant-kit", [config])
        for asset_id, color in (("paper-light", (245, 220, 190, 255)), ("paper-dark", (22, 31, 48, 255))):
            image = Image.new("RGBA", (8, 8), color)
            encoded = BytesIO()
            image.save(encoded, format="PNG")
            write_asset(root, asset_id, data=encoded.getvalue())

        job_dir = self.temp_root / "variant-job"
        job_dir.mkdir()
        job_path = make_test_job(job_dir, theme={"id": "variant-theme", "version": "v001"})
        job = kit.read(job_path)
        job["render_policy_version"] = 1
        job["scenes"] = [
            {"start": 0, "end": 6, "layout": "title", "title": "LIGHT", "body": "TEST", "background_variant": "light"},
            {"start": 6, "end": 12, "layout": "summary", "title": "DARK", "body": "TEST", "background_variant": "dark"},
        ]
        kit.write(job_path, job)
        with patch.object(kit, "ROOT", root):
            composition = kit.Composition(job_path, self.temp_root / "variant-output")
            first = composition.frame(1.0).getpixel((2, 2))
            second = composition.frame(7.0).getpixel((2, 2))
        self.assertEqual(first, (245, 220, 190))
        self.assertEqual(second, (22, 31, 48))

    def test_batch1_first_scene_requires_visible_title_or_hero_media(self):
        job_dir = self.temp_root / "opening-gate"
        job_dir.mkdir()
        job_path = make_test_job(job_dir)
        job = kit.read(job_path)
        job["render_policy_version"] = 1
        job["scenes"][0]["show_title"] = False
        with self.assertRaisesRegex(ValueError, "scene 0: first 3 seconds must show a title or hero visual"):
            kit.validate(job, job_dir)

        kit.write(job_path, job)
        job["scenes"][0].update(layout="media", media={
            "path": "inputs/hero.png", "kind": "image", "role": "illustration",
            "label": "Synthetic hero", "source_id": "test-hero",
        })
        Image.new("RGBA", (32, 32), (90, 120, 150, 255)).save(job_dir / "inputs" / "hero.png")
        job["sources"].append({
            "id": "test-hero", "origin": "synthetic test fixture", "creator": "test",
            "license": "test only", "usage": "TEST ONLY", "checked_date": "2026-10-25",
        })
        self.assertTrue(kit.validate(job, job_dir)["valid"])

    def test_batch1_mascot_breathes_and_blinks_inside_registered_eye_anchors(self):
        for name in ("mascot_breathing_y", "mascot_blink_active", "blink_eyes"):
            self.assertTrue(hasattr(kit, name), f"renderer must provide {name}")
        period = 1.8
        self.assertAlmostEqual(kit.mascot_breathing_y(0), 0.0, places=6)
        self.assertAlmostEqual(kit.mascot_breathing_y(period / 4), 2.5, places=5)
        self.assertAlmostEqual(kit.mascot_breathing_y(3 * period / 4), -2.5, places=5)
        self.assertAlmostEqual(kit.mascot_breathing_y(period), 0.0, places=6)
        self.assertFalse(kit.mascot_blink_active(3.6))
        self.assertTrue(kit.mascot_blink_active(3.7))
        self.assertTrue(kit.mascot_blink_active(3.75))
        self.assertFalse(kit.mascot_blink_active(3.81))
        self.assertTrue(kit.mascot_blink_active(7.4))

        job_dir = self.temp_root / "mascot-secondary-motion"
        job_dir.mkdir()
        job_path = make_test_job(job_dir)
        job = kit.read(job_path)
        job["render_policy_version"] = 1
        kit.write(job_path, job)
        composition = kit.Composition(job_path, self.temp_root / "mascot-secondary-motion-output")
        mascot_size = composition.mouth_rig.pose_data["explain"]["base"].size
        mascot_centers = []
        original_layer = kit.layer
        def capture_mascot_y(im, asset, cx, cy, scale=1, angle=0):
            if asset.size == mascot_size:mascot_centers.append(cy)
            return original_layer(im, asset, cx, cy, scale, angle)
        with patch.object(kit, "layer", side_effect=capture_mascot_y):
            composition.frame(period / 4)
            composition.frame(3 * period / 4)
        base_y = composition.theme["layout"]["mascot_center_px"][1]
        self.assertAlmostEqual(mascot_centers[0], base_y + 2.5, places=5)
        self.assertAlmostEqual(mascot_centers[1], base_y - 2.5, places=5)
        with patch.object(kit, "blink_eyes", wraps=kit.blink_eyes) as blink_spy:
            composition.frame(3.7)
            self.assertEqual(blink_spy.call_count, 1)
            composition.frame(3.81)
            self.assertEqual(blink_spy.call_count, 1)

        registration = kit.read(ROOT / "assets" / "mascot" / "mouth_rig" / "registration.json")
        from PIL import ImageDraw
        for pose in POSES:
            with self.subTest(pose=pose):
                source_path = ROOT / "assets" / "mascot" / "mouth_rig" / "original" / f"{pose}.png"
                with Image.open(source_path) as source:
                    opened = source.convert("RGBA")
                anchors = registration[pose]["source_eye_centers"]
                closed = kit.blink_eyes(opened, anchors)
                before = np.asarray(opened)
                after = np.asarray(closed)
                changed = np.any(before != after, axis=2)
                allowed = Image.new("1", opened.size, 0)
                draw = ImageDraw.Draw(allowed)
                for x, y in anchors:
                    draw.rectangle((round(x - 32), round(y - 24), round(x + 32), round(y + 24)), fill=1)
                self.assertGreater(int(changed.sum()), 0)
                self.assertFalse(np.any(changed & ~np.asarray(allowed, dtype=bool)),
                                 "blink pixels must stay inside registration anchored eye boxes")

    def test_batch1_mascot_side_stays_left_unless_job_opts_into_switching(self):
        self.assertTrue(hasattr(kit, "mascot_right_for_scene"), "renderer must provide the explicit side-lock policy")
        job_dir = self.temp_root / "anchor-lock"
        job_dir.mkdir()
        job_path = make_test_job(job_dir)
        job = kit.read(job_path)
        job["render_policy_version"] = 1
        job["scenes"] = [
            {"start": 0, "end": 6, "layout": "title", "title": "LEFT", "body": "TEST", "right": False},
            {"start": 6, "end": 12, "layout": "summary", "title": "RIGHT", "body": "TEST", "right": True},
        ]
        with self.assertRaisesRegex(ValueError, "scene 1: right-side mascot requires allow_mascot_side_switch=true"):
            kit.validate(job, job_dir)

        job["allow_mascot_side_switch"] = True
        self.assertTrue(kit.validate(job, job_dir)["valid"])
        self.assertFalse(kit.mascot_right_for_scene(job, job["scenes"][0]))
        self.assertTrue(kit.mascot_right_for_scene(job, job["scenes"][1]))

    def test_batch2_visual_element_appears_at_word_cue_with_batch1_pop(self):
        job_path, job, job_dir = self.make_batch2_job("visual-cue")
        job["scenes"][0]["visual_elements"] = [{
            "type": "icon", "icon": "brain_ai", "position": [900, 1300], "cue": 1.0,
        }]
        kit.write(job_path, job)
        composition = kit.Composition(job_path, self.temp_root / "visual-cue-output")
        observed = []
        original_layer = kit.layer

        def capture(im, asset, cx, cy, scale=1, angle=0):
            if asset.size == (kit.PROCEDURAL_ICON_SIZE, kit.PROCEDURAL_ICON_SIZE):
                observed.append((cx, cy, scale))
            return original_layer(im, asset, cx, cy, scale, angle)

        with patch.object(kit, "layer", side_effect=capture):
            composition.frame(0.99)
            self.assertEqual(observed, [], "an icon must stay hidden before its word cue")
            composition.frame(1.0)
            self.assertEqual(len(observed), 1)
            self.assertEqual(observed[-1][2], 0.0)
            composition.frame(1.18)

        self.assertEqual(len(observed), 2)
        self.assertGreater(observed[-1][2], 1.045)
        self.assertLess(observed[-1][2], 1.06)
        self.assertEqual(observed[-1][:2], (900, 1300))

    def test_batch2_visual_element_cue_must_match_a_word_start_in_its_scene(self):
        job_path, job, job_dir = self.make_batch2_job("visual-cue-reject")
        job["scenes"][0]["visual_elements"] = [{
            "type": "icon", "icon": "brain_ai", "position": [900, 1300], "cue": 0.9,
        }]
        with self.assertRaisesRegex(ValueError, "visual element 0: cue must match a word start in scene 0"):
            kit.validate(job, job_dir)

    def test_batch2_visual_element_validator_rejects_unknown_type_and_icon(self):
        job_path, job, job_dir = self.make_batch2_job("visual-icon-reject")
        for element, message in (
            ({"type": "photo", "icon": "brain_ai", "position": [900, 1300], "cue": 1.0},
             "visual element 0: unknown type 'photo'"),
            ({"type": "icon", "icon": "unknown", "position": [900, 1300], "cue": 1.0},
             "visual element 0: unknown icon 'unknown'"),
        ):
            with self.subTest(element=element):
                job["scenes"][0]["visual_elements"] = [element]
                with self.assertRaisesRegex(ValueError, message):
                    kit.validate(job, job_dir)

    def test_batch2_visual_elements_fail_closed_on_protected_zones(self):
        zones = (
            ("mascot", [400, 1200]),
            ("subtitle", [900, 1630]),
            ("footer", [540, 1790]),
            ("progress bar", [540, 1855]),
            ("evidence area", [540, 580]),
        )
        for zone, position in zones:
            with self.subTest(zone=zone):
                job_path, job, job_dir = self.make_batch2_job(f"protected-{zone.replace(' ', '-')}")
                if zone == "evidence area":
                    Image.new("RGBA", (16, 16), (30, 50, 70, 255)).save(job_dir / "inputs" / "evidence.png")
                    job["scenes"][0]["media"] = {
                        "path": "inputs/evidence.png", "kind": "image", "role": "evidence",
                        "label": "Synthetic evidence", "source_id": "test-evidence",
                    }
                    job["sources"].append({
                        "id": "test-evidence", "origin": "synthetic test fixture", "creator": "test",
                        "license": "test only", "usage": "TEST ONLY", "checked_date": "2026-10-25",
                    })
                job["scenes"][0]["visual_elements"] = [{
                    "type": "icon", "icon": "brain_ai", "position": position, "cue": 1.0,
                }]
                with self.assertRaisesRegex(ValueError, f"visual element 0: position overlaps protected {zone}"):
                    kit.validate(job, job_dir)

    def test_batch2_hero_card_can_satisfy_the_first_scene_visual_gate(self):
        job_path, job, job_dir = self.make_batch2_job("hero-opening")
        job["scenes"][0].update(
            show_title=False, template="hero_card", icon="brain_ai", headline="IDEA TO STORY",
        )
        self.assertTrue(kit.validate(job, job_dir)["valid"])
        composition = kit.Composition(job_path, self.temp_root / "hero-opening-output")
        self.assertEqual(composition.frame(0.5).size, (1080, 1920))

    def test_batch2_four_templates_render_procedural_collage_components(self):
        job_path, job, job_dir = self.make_batch2_job("four-templates")
        words = []
        for start, word in ((0.2, "HOOK"), (1.2, "INTRO"), (3.2, "SHELL"), (4.2, "STATUS"),
                            (6.2, "FIRST"), (7.2, "NEXT"), (8.0, "THIRD"), (8.7, "LAST"),
                            (9.2, "AUDIO"), (10.2, "TOOLS"), (10.7, "CHECK"), (11.2, "CHAT")):
            words.append({"word": word, "start": start, "end": start + 0.5})
        kit.write(job_dir / "words.json", words)
        job["scenes"] = [
            {"start": 0, "end": 3, "layout": "title", "title": "HOOK", "pose": "explain",
             "template": "hero_card", "icon": "brain_ai", "headline": "A SIMPLE IDEA"},
            {"start": 3, "end": 6, "layout": "title", "title": "TERMINAL", "pose": "explain",
             "template": "terminal_box", "lines": ["state: ready", "input → idea", "output: storyboard"]},
            {"start": 6, "end": 9, "layout": "title", "title": "FLOW", "pose": "explain",
             "template": "step_flow", "steps": [
                 {"text": "LISTEN", "cue": 6.2}, {"text": "DRAFT", "cue": 7.2},
                 {"text": "REVIEW", "cue": 8.0}, {"text": "SHARE", "cue": 8.7},
             ]},
            {"start": 9, "end": 12, "layout": "title", "title": "FEATURES", "pose": "explain",
             "template": "feature_grid", "features": [
                 {"icon": "audio_wave", "label": "AUDIO", "cue": 9.2},
                 {"icon": "star", "label": "TOOLS", "cue": 10.2},
                 {"icon": "check", "label": "CHECK", "cue": 10.7},
                 {"icon": "chat", "label": "CHAT", "cue": 11.2},
             ]},
        ]
        kit.write(job_path, job)
        composition = kit.Composition(job_path, self.temp_root / "four-templates-output")

        observed_icons = []
        original_draw_icon = kit.draw_procedural_icon

        def capture_icon(icon_name, *args, **kwargs):
            observed_icons.append(icon_name)
            return original_draw_icon(icon_name, *args, **kwargs)

        with patch.object(kit, "draw_procedural_icon", side_effect=capture_icon):
            for index, t in enumerate((0.8, 3.8, 6.8, 9.8)):
                with self.subTest(template=job["scenes"][index]["template"]):
                    scene = composition.j["scenes"][index]
                    frame_with_template = np.asarray(composition.frame(t), dtype=np.uint8)
                    saved = dict(scene)
                    try:
                        scene.pop("template")
                        frame_without_template = np.asarray(composition.frame(t), dtype=np.uint8)
                    finally:
                        scene.clear()
                        scene.update(saved)
                    difference = np.any(frame_with_template[400:920] != frame_without_template[400:920], axis=2)
                    self.assertGreater(int(difference.sum()), 1000)
        self.assertIn("brain_ai", observed_icons)
        self.assertIn("arrow", observed_icons)
        self.assertIn("audio_wave", observed_icons)
        self.assertIn("star", observed_icons)

        original_layer = kit.layer
        entrance_scales = []
        def capture_template_entrance(im, asset, cx, cy, scale=1, angle=0):
            if asset.size in {(860, 350), (860, 370)}:entrance_scales.append((asset.size, scale))
            return original_layer(im, asset, cx, cy, scale, angle)
        with patch.object(kit, "layer", side_effect=capture_template_entrance):
            composition.frame(0.18)
            composition.frame(3.18)
        self.assertEqual([item[0] for item in entrance_scales], [(860, 350), (860, 370)])
        for _, scale in entrance_scales:
            self.assertGreater(scale, 1.045)
            self.assertLess(scale, 1.06)

        flow_scales = []
        def capture_flow(im, asset, cx, cy, scale=1, angle=0):
            if asset.size == (161, 250):flow_scales.append(scale)
            return original_layer(im, asset, cx, cy, scale, angle)
        with patch.object(kit, "layer", side_effect=capture_flow):
            composition.frame(6.8)
            self.assertEqual(flow_scales, [1.0, 0.0, 0.0, 0.0], "step cards must follow their spoken cues in order")
            flow_scales.clear()
            composition.frame(7.38)
        self.assertEqual(len(flow_scales), 4)
        self.assertGreater(flow_scales[1], 1.045)
        self.assertLess(flow_scales[1], 1.06)

        grid_scales = []
        def capture_grid(im, asset, cx, cy, scale=1, angle=0):
            if asset.size == (300, 174):grid_scales.append(scale)
            return original_layer(im, asset, cx, cy, scale, angle)
        with patch.object(kit, "layer", side_effect=capture_grid):
            composition.frame(9.8)
            self.assertEqual(grid_scales, [1.0, 0.0, 0.0, 0.0], "feature cards must stagger at their word cues")
            grid_scales.clear()
            composition.frame(10.38)
        self.assertEqual(len(grid_scales), 4)
        self.assertGreater(grid_scales[1], 1.045)
        self.assertLess(grid_scales[1], 1.06)

    def test_batch2_terminal_box_rejects_executable_or_real_footage_claims(self):
        job_path, job, job_dir = self.make_batch2_job("terminal-guard")
        bad_lines = (
            (["print('hello')"], "terminal_box lines must be inert display text"),
            (["ls -la"], "terminal_box lines must be inert display text"),
            (["REAL FOOTAGE: event capture"], "terminal_box cannot claim real event footage"),
            (["ฟุตเทจเหตุการณ์จริง"], "terminal_box cannot claim real event footage"),
        )
        for lines, message in bad_lines:
            with self.subTest(lines=lines):
                job["scenes"][0].update(template="terminal_box", lines=lines)
                with self.assertRaisesRegex(ValueError, message):
                    kit.validate(job, job_dir)
        for lines in ([], ["one", "two", "three", "four"]):
            with self.subTest(line_count=len(lines)):
                job["scenes"][0].update(template="terminal_box", lines=lines)
                with self.assertRaisesRegex(ValueError, "template terminal_box requires 1–3 short lines"):
                    kit.validate(job, job_dir)

    def test_batch2_procedural_icons_keep_fixed_size_and_take_theme_colors(self):
        self.assertTrue(hasattr(kit, "PROCEDURAL_ICONS"), "renderer must expose the closed icon catalog")
        self.assertTrue(hasattr(kit, "draw_procedural_icon"), "renderer must draw the icon catalog with PIL")
        theme_a = base_theme("icon-color-a")
        theme_b = base_theme("icon-color-b")
        theme_b["palette"] = {"ink": "#132435", "paper": "#F0E0D0", "accents": ["#A020F0", "#2264D8", "#F44336", "#38B577"]}
        for name in kit.PROCEDURAL_ICONS:
            with self.subTest(icon=name):
                first = kit.draw_procedural_icon(name, theme_a)
                second = kit.draw_procedural_icon(name, theme_b)
                self.assertEqual(first.size, (kit.PROCEDURAL_ICON_SIZE, kit.PROCEDURAL_ICON_SIZE))
                self.assertEqual(second.size, first.size)
                self.assertGreater(np.asarray(first.getchannel("A")).sum(), 0)
                self.assertIn((255, 214, 72), set(map(tuple, np.asarray(first.convert("RGB")).reshape(-1, 3))))
                self.assertIn((160, 32, 240), set(map(tuple, np.asarray(second.convert("RGB")).reshape(-1, 3))))


if __name__ == "__main__":
    unittest.main(verbosity=2)
