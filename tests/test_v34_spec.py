"""Guard tests for the locked v3.4 spec constants in renderer/v34_spec.py.

These tests pin the recorded standard so a later edit cannot silently
drift a number, rename a pose, or drop a prop. They do NOT test the v3.4
engine itself: the engine has not been imported into this repo yet
(ENGINE_STATUS must stay "import_pending" until the import lands).
"""
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "renderer"))
import v34_spec


class V34SpecTests(unittest.TestCase):
    def test_engine_status_is_import_pending(self):
        self.assertEqual(v34_spec.ENGINE_STATUS, "import_pending")
        self.assertEqual(v34_spec.SPEC_VERSION, "3.4")

    def test_output_geometry(self):
        self.assertEqual((v34_spec.WIDTH, v34_spec.HEIGHT), (720, 1280))
        self.assertEqual(v34_spec.FPS, 24)
        self.assertEqual(v34_spec.VIDEO_CODEC, "h264")
        self.assertTrue(v34_spec.FASTSTART)
        self.assertEqual(v34_spec.CHUNK_FRAMES, 120)

    def test_render_engine(self):
        self.assertEqual(v34_spec.RENDER_ENGINE, "headless_chromium_cdp")
        self.assertEqual(v34_spec.CAPTURE_JPEG_QUALITY, 92)
        self.assertTrue(v34_spec.LAZY_ASSET_LOADING)

    def test_layout_coordinates(self):
        self.assertEqual(v34_spec.RIBBON_Y, 144)
        self.assertEqual((v34_spec.STAGE_Y_MIN, v34_spec.STAGE_Y_MAX), (214, 659))
        self.assertEqual(v34_spec.SUBTITLE_Y, 672)
        self.assertTrue(v34_spec.SUBTITLE_CENTERED)
        self.assertTrue(v34_spec.SUBTITLE_AUTOFIT)
        self.assertTrue(v34_spec.SUBTITLE_CLEARS_TIKTOK_UI)
        self.assertEqual(v34_spec.MASCOT_SIZE_PX, 500)
        self.assertEqual(v34_spec.MASCOT_BREATHING_PX, 2.2)
        self.assertTrue(v34_spec.MASCOT_STATIC_OUTSIDE_CAMERA_RIG)

    def test_cameras_and_transitions(self):
        self.assertEqual(
            v34_spec.CAMERAS, ("push_in", "pull_out", "focus_tv", "punch_in")
        )
        self.assertEqual(
            v34_spec.TRANSITIONS,
            ("paper_slide", "page_peel", "whip_zoom", "ink_flash"),
        )

    def test_pose_inventory(self):
        self.assertEqual(len(v34_spec.POSES), 16)
        self.assertEqual(len(set(v34_spec.POSES)), 16)
        for name in (
            "wave",
            "pointer",
            "clipboard",
            "confident",
            "magnify",
            "laptop_focus",
            "laptop_smile",
            "cheer",
            "facepalm",
            "thinking_chin",
            "shocked",
            "holding_card",
            "thumbs_up_full",
            "newspaper_hold",
            "shrug",
            "idea_finger",
        ):
            self.assertIn(name, v34_spec.POSES)
        self.assertEqual(v34_spec.CLEAN_PLATE_TOTAL_KB, 220.8)

    def test_mouth_shapes(self):
        self.assertEqual(
            v34_spec.MOUTH_SHAPES, ("CLOSED", "AA", "EE", "OH", "OO", "FV")
        )

    def test_prop_inventory(self):
        self.assertEqual(len(v34_spec.PROPS), 12)
        self.assertEqual(len(set(v34_spec.PROPS)), 12)
        for name in (
            "bot_curious",
            "bot_cheer",
            "bot_shock",
            "badge_alert",
            "badge_check",
            "badge_question",
            "pointer_stick",
            "clipboard",
            "magnifying_glass",
            "laptop",
            "newspaper",
            "lightbulb",
        ):
            self.assertIn(name, v34_spec.PROPS)
        self.assertEqual(v34_spec.PROPS_TOTAL_KB, 88.4)

    def test_tv_slot(self):
        self.assertEqual(v34_spec.TV_SLOT_NAME, "media_clip_frame")
        self.assertEqual(
            (v34_spec.TV_CLIP_MIN_SECONDS, v34_spec.TV_CLIP_MAX_SECONDS), (4, 6)
        )
        self.assertEqual(v34_spec.TV_CLIP_SOURCE, "Lemo-Opuscar")
        self.assertEqual(v34_spec.TV_CLIP_STYLE_COUNT, 25)

    def test_lip_sync_modes(self):
        self.assertEqual(v34_spec.LIP_SYNC_MODES, ("studio", "express"))
        self.assertEqual(v34_spec.LIP_SYNC_EXPRESS_FPS, 24)

    def test_audio_spec(self):
        self.assertEqual(
            v34_spec.BGM_STYLES,
            {"funk_brass": 118, "warm_groove": 108, "mystery_pulse": 104},
        )
        self.assertEqual(v34_spec.BGM_MAIN_STYLE, "funk_brass")
        self.assertEqual(v34_spec.DUCKING_BAND_HZ, (300, 4000))
        self.assertEqual(v34_spec.LOUDNESS_LUFS, -14.5)
        self.assertEqual(v34_spec.LOUDNESS_PASSES, 2)

    def test_required_files_listed(self):
        self.assertIn("renderer/render_liplnwza_v3.py", v34_spec.REQUIRED_ENGINE_FILES)
        self.assertIn("renderer/stage_template.html", v34_spec.REQUIRED_ENGINE_FILES)
        self.assertIn("renderer/widgets.js", v34_spec.REQUIRED_ENGINE_FILES)
        self.assertIn("renderer/audio_mixer.py", v34_spec.REQUIRED_ENGINE_FILES)
        self.assertIn("renderer/mouth_anchors.json", v34_spec.REQUIRED_ENGINE_FILES)


if __name__ == "__main__":
    unittest.main()
