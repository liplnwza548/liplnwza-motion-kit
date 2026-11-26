import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


class V36LivingStageTests(unittest.TestCase):
    def test_stage_template_keeps_y672_and_adds_blocking_and_comic_layers(self):
        html = (ROOT / "renderer" / "stage_template.html").read_text(encoding="utf-8")
        # Locked v3.4 subtitle strip y=672 intact
        self.assertIn("top: 672px;", html)
        # v3.6 mascot blocking presets + flip wrapper + comic layers
        for token in (
            "bg-fx-layer",
            "stage-fx-layer",
            "actor-fx-layer",
            "mascot-flip",
            "shot-left_standard",
            "shot-right_standard",
            "shot-center_stage",
            "shot-closeup_left",
            "shot-closeup_right",
            "shot-closeup_center",
            "shot-peek_left",
            "shot-peek_right",
            "comic-bubble",
            "comic-stamp",
        ):
            self.assertIn(token, html)

    def test_widgets_js_has_subbeats_comic_fx_and_living_widgets(self):
        js = (ROOT / "renderer" / "widgets.js").read_text(encoding="utf-8")
        for token in (
            "applySubBeatAnimations",
            "renderComicFX",
            "w_evidence_card",
            "w_live_calc_receipt",
            "w_bar_compare",
            "stamp_slam",
            "sunburst",
            "comic_burst",
            "magnifying_lens",
            "speed_lines",
            "speech_bubble",
            "beat.mascot_shot",
            "beat.mascot_flip",
        ):
            self.assertIn(token, js)

    def test_renderer_supports_dynamic_fps_and_yuv420p(self):
        py = (ROOT / "renderer" / "render_liplnwza_v3.py").read_text(encoding="utf-8")
        self.assertIn('"--fps"', py)
        self.assertIn('spec.get("fps", FPS)', py)
        self.assertIn("scale=in_range=pc:out_range=tv,format=yuv420p", py)

    def test_audio_mixer_has_comic_foley(self):
        py = (ROOT / "renderer" / "audio_mixer.py").read_text(encoding="utf-8")
        for token in ("synth_stamp_thud", "synth_boing", "synth_cash_ding", "comic_fx", "sfx_cues"):
            self.assertIn(token, py)


    def test_bg_fx_covers_full_canvas_under_rotation(self):
        """Regression guard (PM-v36-sunburst-clip): sunburst & speed_lines must exceed
        farthest corner distance (~923px) and avoid 720x1280 SVG viewport clipping before rotation."""
        js = (ROOT / "renderer" / "widgets.js").read_text(encoding="utf-8")
        self.assertIn("function sunburstSVG(color, rays = 16, r = 1600)", js)
        self.assertIn('viewBox="${-r} ${-r} ${size} ${size}"', js)
        self.assertIn("transform-origin:50% 50%", js)
        self.assertIn("const rOut = 1400;", js)
        self.assertNotIn("const cx = 360, cy = 430, r = 640;", js)
        self.assertNotIn("const rOut = 640;", js)


    def test_bot_props_have_zero_clipped_edges(self):
        """Regression guard: bot_shock, bot_curious, bot_cheer must have transparent padding
        on all 4 edges (edge_touch == 0) so stickers never look cut off."""
        from PIL import Image
        for fname in ("bot_shock.webp", "bot_curious.webp", "bot_cheer.webp"):
            im = Image.open(ROOT / "assets_v3" / "props" / fname).convert("RGBA")
            w, h = im.size
            px = im.getchannel("A").load()
            tl = sum(1 for y in range(h) if px[0, y] > 10)
            tr = sum(1 for y in range(h) if px[w - 1, y] > 10)
            tt = sum(1 for x in range(w) if px[x, 0] > 10)
            tb = sum(1 for x in range(w) if px[x, h - 1] > 10)
            self.assertEqual((tl, tr, tt, tb), (0, 0, 0, 0), f"{fname} touches edge: {(tl, tr, tt, tb)}")


if __name__ == "__main__":
    unittest.main()
