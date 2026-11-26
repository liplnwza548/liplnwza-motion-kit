import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

class V35ModularTests(unittest.TestCase):
    def test_stage_template_has_modular_layouts_and_themes(self):
        html = (ROOT / "renderer" / "stage_template.html").read_text(encoding="utf-8")
        for token in ("layout-split", "layout-full_stage", "mascot-mini_left", "mascot-hidden", "pill-ribbon", "custom-theme-style"):
            self.assertIn(token, html)

    def test_widgets_js_has_custom_html_and_full_bleed(self):
        js = (ROOT / "renderer" / "widgets.js").read_text(encoding="utf-8")
        for token in ("w_custom_html", "custom_html:", "w.fit === 'full_bleed'", "theme.show_stars === false", "theme.ribbon_style === 'pill'", "beat.layout"):
            self.assertIn(token, js)

    def test_renderer_supports_full_bleed_extraction(self):
        py = (ROOT / "renderer" / "render_liplnwza_v3.py").read_text(encoding="utf-8")
        self.assertIn("tw: int = 518, th: int = 310", py)
        self.assertIn('w.get("fit") == "full_bleed"', py)

if __name__ == "__main__":
    unittest.main()
