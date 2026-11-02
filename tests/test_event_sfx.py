"""Event-driven procedural SFX contract tests using TEST ONLY visual cues."""
from __future__ import annotations

import sys
import tempfile
import unittest
import wave
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "renderer"))
import kit


class EventSfxTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="_event_sfx_test_", dir=ROOT / "tests")
        self.temp_root = Path(self.temp.name)

    def tearDown(self):
        self.temp.cleanup()

    def test_trigger_map_covers_batch_one_and_two_visual_event_types(self):
        scenes = [
            {"start": 0, "end": 4, "layout": "title", "show_title": True,
             "aside": "highlight", "cta": "action", "visual_elements": [{"cue": 1.5}]},
            {"start": 4, "end": 8, "layout": "compare", "show_title": False,
             "items": ["A", "B"]},
            {"start": 8, "end": 12, "layout": "title", "show_title": False,
             "template": "hero_card"},
            {"start": 12, "end": 16, "layout": "title", "show_title": False,
             "template": "terminal_box"},
            {"start": 16, "end": 20, "layout": "title", "show_title": False,
             "template": "step_flow", "steps": [{"cue": 17}, {"cue": 18}]},
            {"start": 20, "end": 24, "layout": "title", "show_title": False,
             "template": "feature_grid", "features": [{"cue": 21}, {"cue": 22}]},
            {"start": 24, "end": 28, "layout": "media", "show_title": False,
             "media": {"kind": "image"}},
            {"start": 28, "end": 32, "layout": "list", "show_title": False,
             "items": ["one", "two"]},
            {"start": 32, "end": 36, "layout": "summary", "show_title": False,
             "items": ["one", "two"]},
        ]
        candidates = kit.plan_sfx_event_candidates(36, scenes, render_policy_on=True)
        self.assertEqual(set(kit.SFX_TRIGGER_MAP.values()), {"whoosh", "pop", "ding", "click"})
        self.assertEqual({event["event"] for event in candidates}, set(kit.SFX_TRIGGER_MAP))
        self.assertTrue(all(event["sound"] == kit.SFX_TRIGGER_MAP[event["event"]] for event in candidates))

    def test_event_plan_uses_actual_scene_word_and_visual_cues(self):
        scenes = [
            {"start": 0, "end": 3, "layout": "title", "show_title": False},
            {"start": 3, "end": 6, "layout": "list", "show_title": False,
             "items": ["first", "second"]},
            {"start": 6, "end": 9, "layout": "title", "show_title": False,
             "template": "feature_grid", "features": [
                 {"cue": 6.5}, {"cue": 7.2},
             ], "visual_elements": [{"cue": 8.0}]},
            {"start": 9, "end": 12, "layout": "title", "show_title": False,
             "cta": "TEST CTA"},
        ]
        candidates = kit.plan_sfx_event_candidates(12, scenes, render_policy_on=True)
        timed = {(event["event"], event["time"], event["target"]) for event in candidates}
        self.assertIn(("scene_card_enter", .1, "scene_card"), timed)
        self.assertIn(("list_item_enter", 3.1, "list_item:0"), timed)
        self.assertIn(("list_item_enter", 3.4, "list_item:1"), timed)
        self.assertIn(("feature_card_enter", 6.5, "feature:0"), timed)
        self.assertIn(("feature_card_enter", 7.2, "feature:1"), timed)
        self.assertIn(("visual_icon_cue", 8.0, "visual_icon:0"), timed)
        self.assertIn(("cta_enter", 9.7, "cta"), timed)

    def test_event_sfx_file_triggers_on_cues_and_throttles_crowded_events(self):
        scene = {
            "start": 0, "end": 3, "layout": "list", "show_title": False,
            "items": ["one", "two", "three", "four"],
            "visual_elements": [{"cue": 1.4}, {"cue": 2.0}],
        }
        output = self.temp_root / "event-sfx.wav"
        events = kit.make_sfx(3, [scene], output, event_driven=True)
        self.assertTrue(output.is_file())
        self.assertTrue(all(event["sound"] in {"whoosh", "pop", "ding", "click"} for event in events))
        self.assertTrue(any(event["event"] == "visual_icon_cue" and event["time"] == 1.4 for event in events))
        self.assertTrue(any(event["event"] == "visual_icon_cue" and event["time"] == 2.0 for event in events))
        self.assertTrue(all(b["time"] - a["time"] >= kit.SFX_EVENT_MIN_GAP_S
                            for a, b in zip(events, events[1:])))
        with wave.open(str(output), "rb") as source:
            self.assertEqual(source.getframerate(), 48000)
            self.assertEqual(source.getnchannels(), 2)
            self.assertEqual(source.getnframes(), 3 * 48000)
            samples = np.frombuffer(source.readframes(source.getnframes()), dtype="<i2")
        self.assertGreater(np.max(np.abs(samples)), 0)

    def test_procedural_foley_clips_are_deterministic_and_have_distinct_envelopes(self):
        expected_seconds = {"whoosh": .25, "pop": .11, "ding": .38, "click": .035}
        for sound, seconds in expected_seconds.items():
            first = kit.procedural_sfx_clip(sound, np.random.default_rng(5))
            again = kit.procedural_sfx_clip(sound, np.random.default_rng(5))
            self.assertEqual(len(first), round(seconds * 48000))
            self.assertTrue(np.array_equal(first, again), sound)
            self.assertGreater(float(np.max(np.abs(first))), 0.01, sound)
            self.assertLessEqual(float(np.max(np.abs(first))), 0.151, sound)
        ding = kit.procedural_sfx_clip("ding", np.random.default_rng(7))
        self.assertGreater(float(np.sqrt(np.mean(ding[:4800] ** 2))),
                           float(np.sqrt(np.mean(ding[-4800:] ** 2))))

    def test_policy_gate_preserves_legacy_offsets_until_opted_in(self):
        self.assertFalse(kit.sfx_events_enabled({}))
        self.assertTrue(kit.sfx_events_enabled({"render_policy_version": 1}))
        self.assertTrue(kit.sfx_events_enabled({"sfx_policy": "event_v1"}))
        with self.assertRaisesRegex(ValueError, "Unsupported render_policy_version"):
            kit.sfx_events_enabled({"render_policy_version": 2})
        with self.assertRaisesRegex(ValueError, "sfx_policy must be"):
            kit.sfx_events_enabled({"sfx_policy": "enabled"})

        output = self.temp_root / "legacy-sfx.wav"
        events = kit.make_sfx(4, [{"start": 0, "end": 4}], output)
        self.assertEqual(events, [
            {"time": .02, "sound": "swish"}, {"time": .3, "sound": "pop"},
            {"time": .82, "sound": "tap"}, {"time": 1.4, "sound": "pop"},
            {"time": 2.3, "sound": "ding"},
        ])


if __name__ == "__main__":
    unittest.main(verbosity=2)
