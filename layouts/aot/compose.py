#!/usr/bin/env python3
"""Generic AoT-layout compositor (PIL frames + ffmpeg, no AI video).

Layout (locked 2026-11-02, see SPEC.md in this folder):
  1080x1920, 30fps, bg #FFF6E8 with dot grid
  top:    frame x48..1032, y48..928 (header #FFE9A8 96px + image
          centre-crop cover 984x784, hard cuts at beat boundaries,
          no zoom/pan/overlay)
  chips:  strip y915..1255, paper chips, Prompt-Bold, palette
          yellow/blue/red/green, max 3 words per row, spring
          0.6x -> 1.08x -> 1.0x in 0.13s (locked 2026-11-05).
          Optional per-word "role" in words.json overrides the
          cycling palette (see SPEC.md).
  mascot: PoseMouthRig frames (master lock + rig only, from
          assets/mascot/mouth_rig/), scaled uniformly 1.2x (A-fixed,
          approved 2026-11-05), alpha-bbox centre x=540, alpha-bbox
          bottom anchored at y=1872 + bob (amplitude 7px). The
          chips/mascot gap is frame-dependent (see SPEC.md); it is
          verified by frame QC, not by a static assert.

This file is generic: no topic, voice, image or beat from any earlier
clip is hardcoded. Everything a clip needs comes from its job folder.

Job format (all paths relative to the job folder):
  {
    "schema_version": 1, "layout": "aot-v001", "title": "...",
    "voice": "voice.wav", "words": "words.json", "visemes": "visemes.json",
    "beats": [{"name": "B01", "start": 0.0, "end": 3.0, "image": "beat-01.png"}],
    "images": {"B01": {"file": "beat-01.png", "status": "accepted", "sha256": "..."}},
    "poses": [{"at": 0.0, "pose": "thinking"}]   (optional; defaults to cycling poses at beats)
    "junctions": [5.15, 9.94]                    (optional sentence boundaries)
    # Optional per beat: "banner" (<=4 tokens, else a hard error),
    # "bg" (pastel hex, e.g. "#DDEBFF"), "widgets" (list, see SPEC.md).
    # Optional top level: "sfx": [{"at": 1.2, "file": "pop.wav", "gain": 1.0}],
    # "bgm": {"file": "bed.wav", "gain": 0.3}. Audio files come from the
    # job only; nothing is bundled in this repo. No new field is ever
    # required: a job without them renders exactly as before, except
    # for the locked chip spring (see spring_scale).
  }
Words are a bare list [{"word": ..., "start": ..., "end": ...}] or
{"words": [...]}. Visemes are [{"start": ..., "shape": ...}].

P2 GUARD: OFF = 0.08 must not change without Philip's sync-test decision.

Usage:
  python layouts/aot/compose.py --job <job.json> --out <video.mp4>
  python layouts/aot/compose.py --job <job.json> --stills <dir>
  python layouts/aot/compose.py --job <job.json> --out <video.mp4> --max-frames 90
"""
import argparse
import hashlib
import json
import math
import subprocess
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageFilter

ROOT = Path(__file__).resolve().parents[2]
FPS, W, H = 30, 1080, 1920
OFF = 0.08  # P2 GUARD: do not change without Philip's sync-test decision
FRAME_X, FRAME_Y, FRAME_W, FRAME_H = 48, 48, 984, 880
HEADER_H = 96
IMG_W, IMG_H = 984, 784
CHIP_Y, CHIP_H = 915, 340
# A-fixed mascot placement (approved 2026-11-05): the rig frame is
# scaled uniformly 1.2x, its alpha bbox is centred on x=540, and its
# alpha-bbox bottom is anchored at MASCOT_BOTTOM_Y + bob. The old
# static assert (canvas top y1282 minus bob vs chip-strip end) is
# deliberately NOT carried over: with alpha-bbox anchoring, the
# mascot top varies per pose and per viseme (mouth shapes change the
# bbox every frame), so no single static number can prove the gap.
# The gap is therefore a frame-QC check, not an import-time assert:
# at the A-fixed test frame (t=4.10s, pose explain) the visible
# mascot was 600x597px with its top at y=1269 — 14px below the chip
# strip's end (y=1255) and 63px below the lowest actual chip pixel
# (y=1206) in that frame. The bottom anchor itself is still guarded
# below: MASCOT_BOTTOM_Y + BOB_PX must stay inside the frame.
MASCOT_SCALE = 1.2
MASCOT_CENTRE_X = 540
MASCOT_BOTTOM_Y = 1872
BOB_PX = 7
assert MASCOT_BOTTOM_Y + BOB_PX <= H, "mascot bottom anchor leaves the frame"
BG = (255, 246, 232)
HEADER = (255, 233, 168)
INK = (24, 27, 38)
PALETTE = [(255, 214, 72), (34, 100, 216), (244, 67, 54), (56, 181, 119)]
PALETTE_TEXT = [(24, 27, 38), (255, 253, 246), (255, 253, 246), (24, 27, 38)]
# Word-role colours (locked 2026-11-05). A word's "role" comes from the
# job's words.json only; the renderer never guesses a role from text.
ROLE_COLORS = {
    "emphasis": ((255, 214, 72), (24, 27, 38)),    # condition / emphasis: yellow
    "tool": ((34, 100, 216), (255, 253, 246)),     # tool name / command: blue
    "result": ((56, 181, 119), (24, 27, 38)),      # good result: green
    "verb": ((244, 67, 54), (255, 253, 246)),      # key verb: red
    "connector": ((255, 253, 246), (24, 27, 38)),  # connector word: white, dark ink
}
SPRING_DURATION = 0.13  # locked chip spring duration (seconds)
STAGGER_S = 0.12        # locked stagger between sub-elements of one widget
WIDGET_TYPES = ("highlight", "container", "typewriter", "cta")
POSES = ("explain", "point_right", "thinking", "magnify", "point_left", "thumbs_up")
FONT_PATH = ROOT / "assets" / "fonts" / "Prompt-Bold.ttf"


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while True:
            chunk = f.read(1 << 20)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


def spring_scale(u):
    """Locked spring (2026-11-05): 0.6x at u=0, ~1.08x at u=0.5, 1.0x at u=1."""
    if u <= 0:
        return 0.6
    if u >= 1:
        return 1.0
    if u < 0.5:
        f = (1 - math.cos(math.pi * (u / 0.5))) / 2
        return 0.6 + (1.08 - 0.6) * f
    f = (1 - math.cos(math.pi * ((u - 0.5) / 0.5))) / 2
    return 1.08 + (1.0 - 1.08) * f


def parse_hex_color(value, where):
    """Parse '#RRGGBB' into an (r, g, b) tuple, or raise a clear error."""
    if not isinstance(value, str) or len(value) != 7 or not value.startswith("#"):
        raise ValueError(f"{where} must be a hex colour like '#DDEBFF', got {value!r}")
    try:
        return tuple(int(value[i:i + 2], 16) for i in (1, 3, 5))
    except ValueError:
        raise ValueError(f"{where} must be a hex colour like '#DDEBFF', got {value!r}")


def dot_color_for(bg_rgb):
    """A darker dot-grid colour derived from a background colour."""
    return tuple(max(0, c - 45) for c in bg_rgb)


def draw_text_centred(draw, cx, cy, text, fnt, fill):
    bb = fnt.getbbox(text)
    w, h = bb[2] - bb[0], bb[3] - bb[1]
    draw.text((cx - w / 2 - bb[0], cy - h / 2 - bb[1]), text, font=fnt, fill=fill)
    return w


def cover_crop(im, tw, th):
    w, h = im.size
    s = max(tw / w, th / h)
    im2 = im.convert("RGB").resize((round(w * s), round(h * s)), Image.Resampling.LANCZOS)
    x = (im2.width - tw) // 2
    y = (im2.height - th) // 2
    return im2.crop((x, y, x + tw, y + th))


def font(size):
    return ImageFont.truetype(str(FONT_PATH), size, layout_engine=ImageFont.Layout.RAQM)


def clean_alpha(im):
    r, g, b, a = im.split()
    a2 = a.point(lambda p: 0 if p <= 40 else min(255, (p - 40) * 255 // (255 - 40)))
    a2 = a2.filter(ImageFilter.MinFilter(3))
    return Image.merge("RGBA", (r, g, b, a2))


def dedupe_visemes(visemes):
    """One shape per timestamp, LAST shape wins (documented choice)."""
    by_ts = {}
    for v in visemes:
        by_ts[v["start"]] = v["shape"]
    return [{"start": s, "shape": by_ts[s]} for s in sorted(by_ts)]


def build_rows(words, junctions):
    """Rows: never mix sentences (when junctions given), max 3 words, max 1.2s span."""
    sents = [[]]
    for w in words:
        if junctions and sents[-1] and any(
            sents[-1][-1]["start"] < j <= w["start"] for j in junctions
        ):
            sents.append([])
        sents[-1].append(w)
    rows = []
    for sent in sents:
        grp = []
        for w in sent:
            if grp and (len(grp) == 3 or w["end"] - grp[0]["start"] > 1.2):
                rows.append(grp)
                grp = []
            grp.append(w)
        if grp:
            rows.append(grp)
    return rows


class ChipStrip:
    def __init__(self, words, junctions):
        self.rows = build_rows(words, junctions)
        self._base = {}

    def frame(self, t):
        im = Image.new("RGBA", (W, CHIP_H))
        for ri, grp in enumerate(self.rows):
            show = grp[0]["start"] + OFF
            clear = grp[-1]["end"] + OFF
            if not (show <= t < clear):
                continue
            # Widths at 80px, scaled to fit 960px max.
            widths = []
            for w in grp:
                bb = font(80).getbbox(w["word"])
                widths.append(max(112, bb[2] - bb[0] + 68))
            total = sum(widths) + 18 * (len(widths) - 1)
            scale = min(1, 960 / total)
            x = (W - total * scale) / 2
            for wi, (w, w0) in enumerate(zip(grp, widths)):
                width = round(w0 * scale)
                role = w.get("role")
                key = (ri, wi, width, role)
                if key not in self._base:
                    if role in ROLE_COLORS:
                        col, txt_col = ROLE_COLORS[role]
                    else:
                        col = PALETTE[wi % 4]
                        txt_col = PALETTE_TEXT[wi % 4]
                    chip = Image.new("RGBA", (width, 140), (0, 0, 0, 0))
                    d = ImageDraw.Draw(chip)
                    d.rounded_rectangle((6, 6, width - 6, 134), radius=18, fill=col, outline=INK, width=4)
                    f = font(round(80 * scale))
                    bb = f.getbbox(w["word"])
                    d.text(((width - (bb[2] - bb[0])) / 2 - bb[0], (140 - (bb[3] - bb[1])) / 2 - bb[1]),
                           w["word"], font=f, fill=txt_col)
                    self._base[key] = chip
                if t < w["start"] + OFF:
                    pass
                elif t < w["start"] + OFF + SPRING_DURATION:
                    s = spring_scale((t - w["start"] - OFF) / SPRING_DURATION)
                    chip = self._base[key].resize(
                        (max(1, round(width * s)), max(1, round(140 * s))), Image.Resampling.BICUBIC)
                    angle = 2 if wi % 2 else -2
                    chip = chip.rotate(angle, Image.Resampling.BICUBIC, expand=True)
                    im.alpha_composite(chip, (round(x + width / 2 - chip.width / 2),
                                              round(165 - chip.height / 2)))
                else:
                    chip = self._base[key].rotate(2 if wi % 2 else -2, Image.Resampling.BICUBIC, expand=True)
                    im.alpha_composite(chip, (round(x + width / 2 - chip.width / 2),
                                              round(165 - chip.height / 2)))
                x += width + 18 * scale
        return im


def load_job(job_path):
    job_path = Path(job_path)
    job_dir = job_path.parent
    job = read_json(job_path)
    if job.get("layout") != "aot-v001":
        raise ValueError(f"job layout must be aot-v001, got {job.get('layout')!r}")
    beats = job["beats"]
    if not beats:
        raise ValueError("job beats must not be empty")
    for i in range(1, len(beats)):
        if beats[i]["start"] < beats[i - 1]["end"] - 1e-9:
            raise ValueError(f"beats overlap/gap at {beats[i]['name']}")
    if beats[0]["start"] > 0.05:
        raise ValueError("first beat must start at (or very near) 0.0, else frame 0 has no image")
    # Optional locked-formula fields, validated loudly (never silently
    # truncated or guessed): banner <= 4 tokens, bg = hex colour,
    # widgets well-formed and inside their beat, audio files present.
    for beat in beats:
        if "banner" in beat:
            if not isinstance(beat["banner"], str) or not beat["banner"].strip():
                raise ValueError(f"beat {beat['name']} banner must be non-empty text")
            if len(beat["banner"].split()) > 4:
                raise ValueError(
                    f"beat {beat['name']} banner has more than 4 words: {beat['banner']!r}")
        if "bg" in beat:
            parse_hex_color(beat["bg"], f"beat {beat['name']} bg")
        for wdg in beat.get("widgets", []):
            if not isinstance(wdg, dict) or wdg.get("type") not in WIDGET_TYPES:
                raise ValueError(f"beat {beat['name']} has an unknown widget: {wdg!r}")
            ws, we = wdg.get("start"), wdg.get("end")
            if ws is None or we is None or not (beat["start"] - 1e-9 <= ws < we <= beat["end"] + 1e-9):
                raise ValueError(
                    f"beat {beat['name']} widget {wdg.get('type')} window "
                    f"[{ws}, {we}] must lie inside the beat [{beat['start']}, {beat['end']}]")
            if wdg["type"] == "container" and (not wdg.get("items") or not wdg.get("box") or not wdg.get("target")):
                raise ValueError(f"beat {beat['name']} container widget needs items, box and target")
            if wdg["type"] == "typewriter" and not wdg.get("text"):
                raise ValueError(f"beat {beat['name']} typewriter widget needs text")
            if wdg["type"] == "cta" and (not wdg.get("profile") or not wdg.get("keyword")):
                raise ValueError(f"beat {beat['name']} cta widget needs profile and keyword")
    for ev in job.get("sfx", []):
        if not isinstance(ev, dict) or "at" not in ev or "file" not in ev:
            raise ValueError(f"sfx events need at and file: {ev!r}")
        if not (0 <= float(ev.get("gain", 1.0)) <= 2.0):
            raise ValueError(f"sfx gain must be 0..2: {ev!r}")
        if not (job_dir / ev["file"]).exists():
            raise FileNotFoundError(f"sfx file missing: {job_dir / ev['file']}")
    bgm = job.get("bgm")
    if bgm is not None:
        if not isinstance(bgm, dict) or "file" not in bgm:
            raise ValueError(f"bgm needs a file: {bgm!r}")
        if not (0 <= float(bgm.get("gain", 0.3)) <= 2.0):
            raise ValueError(f"bgm gain must be 0..2: {bgm!r}")
        if not (job_dir / bgm["file"]).exists():
            raise FileNotFoundError(f"bgm file missing: {job_dir / bgm['file']}")
    images = job.get("images", {})
    for beat in beats:
        entry = images.get(beat["name"])
        if entry is None:
            raise ValueError(f"beat {beat['name']} has no entry in job images manifest")
        if entry.get("status") != "accepted":
            raise ValueError(f"beat {beat['name']} is not accepted in the manifest")
        p = job_dir / entry["file"]
        if not p.exists():
            raise FileNotFoundError(f"manifest image missing: {p}")
        if entry.get("sha256") and sha256_file(p) != entry["sha256"]:
            raise ValueError(f"manifest sha mismatch for beat {beat['name']}")
        with Image.open(p) as _im:
            if _im.size[0] < 1024 or _im.size[1] < 768:
                raise ValueError(f"panel {beat['name']} too small (minimum 1024x768)")
    words = read_json(job_dir / job["words"])
    if isinstance(words, dict):
        words = words["words"]
    visemes = read_json(job_dir / job["visemes"])
    if isinstance(visemes, dict):
        visemes = visemes["visemes"]
    return job, job_dir, beats, words, visemes


def draw_pill(draw, x, y, w, h, text, fnt, fill, txt_fill):
    """A small rounded pill with centred text; returns nothing."""
    draw.rounded_rectangle((x, y, x + w, y + h), radius=16, fill=fill, outline=INK, width=4)
    draw_text_centred(draw, x + w / 2, y + h / 2, text, fnt, txt_fill)


def widget_frame(frame, beat, t):
    """Draw a beat's panel widgets (never over chips or the mascot).

    Widgets live in the top panel area (or, for a CTA pill, in the
    strip below the mascot). They are drawn over the panel for their
    window only; they never cover the chip strip or the mascot.
    All text comes from the job; nothing is invented here.
    """
    panel_x, panel_y = FRAME_X, FRAME_Y + HEADER_H
    panel_w, panel_h = IMG_W, IMG_H
    for wdg in beat.get("widgets", []):
        if not (wdg["start"] <= t < wdg["end"]):
            continue
        dur = wdg["end"] - wdg["start"]
        u = (t - wdg["start"]) / dur if dur > 0 else 1.0
        if wdg["type"] == "highlight":
            # Contrasting sweep across the header bar (NOT yellow on
            # yellow, the flaw in the first locked test): a translucent
            # red band sweeps left->right over 1.2s, then tints the bar.
            ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
            od = ImageDraw.Draw(ov)
            hx0, hy0, hx1, hy1 = FRAME_X, FRAME_Y, FRAME_X + FRAME_W, FRAME_Y + HEADER_H
            prog = min(1.0, (t - wdg["start"]) / 1.2)
            if prog < 1.0:
                bx0 = hx0 + (hx1 - hx0 - 320) * prog
                od.rectangle((bx0, hy0, bx0 + 320, hy1), fill=(244, 67, 54, 120))
            else:
                od.rectangle((hx0, hy0, hx1, hy1), fill=(244, 67, 54, 60))
                od.rectangle((hx0, hy1 - 8, hx1, hy1), fill=(244, 67, 54))
            frame.paste(ov, (0, 0), ov)
        elif wdg["type"] == "container":
            # Items pop in staggered 0.12s, shrink into the box, then
            # the box slides into the target window and the target pops.
            items = list(wdg["items"])
            ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
            od = ImageDraw.Draw(ov)
            box_cx, box_cy = panel_x + panel_w * 0.32, panel_y + panel_h * 0.62
            tgt_cx, tgt_cy = panel_x + panel_w * 0.74, panel_y + panel_h * 0.62
            # Target window (always visible during the widget window).
            od.rounded_rectangle((tgt_cx - 130, tgt_cy - 110, tgt_cx + 130, tgt_cy + 110),
                                 radius=20, outline=INK, width=4)
            draw_text_centred(od, tgt_cx, tgt_cy - 130, str(wdg["target"]), font(44), INK)
            if u < 0.4:
                # Phase 1: items in a row, staggered.
                row_y = panel_y + 190
                widths = []
                for it in items:
                    bb = font(44).getbbox(str(it))
                    widths.append(bb[2] - bb[0] + 56)
                total = sum(widths) + 16 * (len(widths) - 1)
                x = panel_x + (panel_w - total) / 2
                for j, (it, iw) in enumerate(zip(items, widths)):
                    if t >= wdg["start"] + j * STAGGER_S:
                        sc = spring_scale(min(1.0, (t - (wdg["start"] + j * STAGGER_S)) / SPRING_DURATION))
                        w2, h2 = round(iw * sc), round(96 * sc)
                        draw_pill(od, x + (iw - w2) / 2, row_y + (96 - h2) / 2, w2, h2,
                                  str(it), font(max(12, round(44 * sc))), PALETTE[j % 4],
                                  PALETTE_TEXT[j % 4])
                    x += iw + 16
                # Box, empty for now.
                od.rounded_rectangle((box_cx - 150, box_cy - 100, box_cx + 150, box_cy + 100),
                                     radius=20, fill=(255, 253, 246), outline=INK, width=4)
                draw_text_centred(od, box_cx, box_cy - 120, str(wdg["box"]), font(44), INK)
            elif u < 0.7:
                # Phase 2: items shrink into the box (drawn as dots).
                f = (u - 0.4) / 0.3
                od.rounded_rectangle((box_cx - 150, box_cy - 100, box_cx + 150, box_cy + 100),
                                     radius=20, fill=(255, 253, 246), outline=INK, width=4)
                draw_text_centred(od, box_cx, box_cy - 120, str(wdg["box"]), font(44), INK)
                for j in range(len(items)):
                    cx = box_cx - 60 + j * 60
                    od.ellipse((cx - 14 * (1 - f * 0.5), box_cy - 14 * (1 - f * 0.5),
                                cx + 14 * (1 - f * 0.5), box_cy + 14 * (1 - f * 0.5)),
                               fill=PALETTE[j % 4], outline=INK, width=3)
            else:
                # Phase 3: box slides into the target window.
                f = (u - 0.7) / 0.3
                cx = box_cx + (tgt_cx - box_cx) * f
                cy = box_cy
                sc = 1.0 - 0.4 * f
                w2, h2 = round(300 * sc), round(200 * sc)
                od.rounded_rectangle((cx - w2 / 2, cy - h2 / 2, cx + w2 / 2, cy + h2 / 2),
                                     radius=20, fill=(255, 253, 246), outline=INK, width=4)
                draw_text_centred(od, cx, cy, str(wdg["box"]), font(44), INK)
                if f > 0.8:
                    draw_text_centred(od, tgt_cx, tgt_cy + 140, "✓", font(56), (56, 181, 119))
            frame.paste(ov, (0, 0), ov)
        elif wdg["type"] == "typewriter":
            # A command box in the panel: text typed char by char, then
            # a green tick with burst lines.
            text = str(wdg["text"])
            bx, by, bw, bh = panel_x + 72, panel_y + panel_h // 2 - 130, panel_w - 144, 260
            ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
            od = ImageDraw.Draw(ov)
            od.rounded_rectangle((bx, by, bx + bw, by + bh), radius=20,
                                 fill=(255, 253, 246), outline=INK, width=4)
            n_chars = min(len(text), int((t - wdg["start"]) / 0.08))
            shown = text[:n_chars]
            # Simple wrap by tokens so long Thai phrases stay inside.
            lines, cur = [], ""
            for tok in shown.split(" "):
                trial = (cur + " " + tok).strip()
                if font(48).getbbox(trial)[2] - font(48).getbbox(trial)[0] > bw - 64 and cur:
                    lines.append(cur)
                    cur = tok
                else:
                    cur = trial
            if cur:
                lines.append(cur)
            for li, line in enumerate(lines[:3]):
                od.text((bx + 32, by + 32 + li * 62), line, font=font(48), fill=INK)
            if n_chars >= len(text):
                tx, ty = bx + bw - 70, by + bh - 70
                od.ellipse((tx - 34, ty - 34, tx + 34, ty + 34), fill=(56, 181, 119), outline=INK, width=4)
                od.line((tx - 18, ty, tx - 5, ty + 14), fill=(255, 253, 246), width=6)
                od.line((tx - 5, ty + 14, tx + 20, ty - 16), fill=(255, 253, 246), width=6)
                for k in range(8):
                    ang = 2 * math.pi * k / 8
                    od.line((tx + 44 * math.cos(ang), ty + 44 * math.sin(ang),
                             tx + 66 * math.cos(ang), ty + 66 * math.sin(ang)),
                            fill=(244, 67, 54), width=5)
            frame.paste(ov, (0, 0), ov)
        elif wdg["type"] == "cta":
            # A profile card in the panel (text/initial only, never a
            # real photo): card pops, follow button flips after a
            # stagger, keyword types into the comment box. The pill
            # below the mascot is drawn separately, after the mascot.
            bx, by, bw, bh = panel_x + 112, panel_y + panel_h // 2 - 160, panel_w - 224, 320
            ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
            od = ImageDraw.Draw(ov)
            sc = spring_scale(min(1.0, (t - wdg["start"]) / SPRING_DURATION))
            w2, h2 = round(bw * sc), round(bh * sc)
            cx, cy = bx + bw / 2, by + bh / 2
            od.rounded_rectangle((cx - w2 / 2, cy - h2 / 2, cx + w2 / 2, cy + h2 / 2),
                                 radius=20, fill=(255, 253, 246), outline=INK, width=4)
            if sc >= 1.0:
                profile = str(wdg["profile"])
                od.ellipse((bx + 36, by + 36, bx + 132, by + 132), fill=(34, 100, 216), outline=INK, width=4)
                draw_text_centred(od, bx + 84, by + 84, profile[:1], font(56), (255, 253, 246))
                od.text((bx + 156, by + 52), profile, font=font(48), fill=INK)
                follow = "ติดตามแล้ว" if t >= wdg["start"] + STAGGER_S else "ติดตาม"
                fcol = (56, 181, 119) if follow == "ติดตามแล้ว" else (34, 100, 216)
                fb = font(40).getbbox(follow)
                fw = fb[2] - fb[0] + 56
                draw_pill(od, bx + bw - fw - 36, by + 44, fw, 64, follow, font(40), fcol, (255, 253, 246))
                # Comment box: keyword typed from start + 2 staggers.
                kw = str(wdg["keyword"])
                n_chars = min(len(kw), int(max(0, t - (wdg["start"] + 2 * STAGGER_S)) / 0.12))
                od.rounded_rectangle((bx + 36, by + 176, bx + bw - 36, by + 260),
                                     radius=16, outline=INK, width=3)
                od.text((bx + 56, by + 196), kw[:n_chars], font=font(44), fill=INK)
            frame.paste(ov, (0, 0), ov)


def cta_pill_frame(frame, beat, t):
    """Draw a CTA pill in the strip below the mascot, if one is active."""
    for wdg in beat.get("widgets", []):
        if wdg["type"] != "cta" or not wdg.get("below_mascot"):
            continue
        if not (wdg["start"] <= t < wdg["end"]):
            continue
        txt = str(wdg.get("pill") or wdg["keyword"])
        cf = font(44)
        bb = cf.getbbox(txt)
        pw, ph = bb[2] - bb[0] + 72, 56
        sc = spring_scale(min(1.0, (t - wdg["start"]) / SPRING_DURATION)) if t < wdg["start"] + SPRING_DURATION else 1.0
        w2, h2 = max(1, round(pw * sc)), max(1, round(ph * sc))
        pill = Image.new("RGBA", (w2, h2), (0, 0, 0, 0))
        pd = ImageDraw.Draw(pill)
        pd.rounded_rectangle((3, 3, w2 - 3, h2 - 3), radius=16, fill=(255, 214, 72), outline=INK, width=4)
        bf = font(round(44 * sc))
        bb2 = bf.getbbox(txt)
        pd.text(((w2 - (bb2[2] - bb2[0])) / 2 - bb2[0], (h2 - (bb2[3] - bb2[1])) / 2 - bb2[1]),
                txt, font=bf, fill=INK)
        frame.paste(pill, ((W - w2) // 2, 1852 + (ph - h2) // 2), pill)


def mix_audio(job, job_dir, voice_path, out_dir):
    """Mix voice + optional job sfx/bgm into one wav.

    Returns the voice path unchanged when the job gives no sfx/bgm.
    SFX/BGM files come from the job only; this function never invents
    audio and never writes audio into the repo. A synthetic test tone
    is only a code test, never a real SFX.
    """
    sfx = job.get("sfx") or []
    bgm = job.get("bgm")
    if not sfx and not bgm:
        return str(voice_path)
    import wave as _wave
    with _wave.open(str(voice_path), "rb") as wav:
        dur = wav.getnframes() / wav.getframerate()
    out_path = Path(out_dir) / "mixed-audio.wav"
    cmd = ["ffmpeg", "-y", "-v", "error"]
    inputs = [str(voice_path)]
    for ev in sfx:
        inputs.append(str(job_dir / ev["file"]))
    bgm_idx = None
    if bgm is not None:
        cmd += ["-stream_loop", "-1"]
        bgm_idx = len(inputs)
        inputs.append(str(job_dir / bgm["file"]))
    for inp in inputs:
        cmd += ["-i", inp]
    filters = []
    labels = ["[0:a]"]
    for i, ev in enumerate(sfx):
        ms = int(float(ev["at"]) * 1000)
        filters.append(f"[{i + 1}:a]adelay={ms}|{ms},volume={float(ev.get('gain', 1.0))}[sfx{i}]")
        labels.append(f"[sfx{i}]")
    if bgm_idx is not None:
        filters.append(f"[{bgm_idx}:a]volume={float(bgm.get('gain', 0.3))}[bgm]")
        labels.append("[bgm]")
    filters.append(f"{''.join(labels)}amix=inputs={len(labels)}:normalize=0[aout]")
    cmd += ["-filter_complex", ";".join(filters), "-map", "[aout]", "-t", str(dur), str(out_path)]
    subprocess.run(cmd, check=True)
    return str(out_path)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--job", required=True)
    ap.add_argument("--out", default=None)
    ap.add_argument("--stills", default=None, help="write 3 still PNGs (0.5s, mid, near-end) and exit")
    ap.add_argument("--max-frames", type=int, default=None)
    ap.add_argument("--frames-dir", default=None)
    args = ap.parse_args()
    job, job_dir, beats, words, visemes = load_job(args.job)
    sys.path.insert(0, str(ROOT / "assets" / "mascot" / "mouth_rig"))
    from rig_motion import PoseMouthRig

    voice = job_dir / job["voice"]
    # Per-beat backgrounds (locked formula 3): default cream, or the
    # beat's pastel "bg" hex. Dot grid is drawn only below the top
    # frame, as in the proven layout, and changes with the beat.
    bgs = []
    for beat in beats:
        bg_rgb = parse_hex_color(beat["bg"], f"beat {beat['name']} bg") if "bg" in beat else BG
        bg = Image.new("RGB", (W, H), bg_rgb)
        d = ImageDraw.Draw(bg)
        dc = dot_color_for(bg_rgb)
        for yy in range(980, H, 56):
            for xx in range(56, W, 56):
                d.ellipse((xx - 2, yy - 2, xx + 2, yy + 2), fill=dc)
        bgs.append(bg)

    # Top panels, pre-cropped to the image area 984x784.
    panels = []
    for beat in beats:
        entry = job["images"][beat["name"]]
        panels.append(cover_crop(Image.open(job_dir / entry["file"]), IMG_W, IMG_H))
    browsers = []
    for beat, pimg in zip(beats, panels):
        fr = Image.new("RGB", (FRAME_W, FRAME_H), HEADER)
        fr.paste(pimg, (0, HEADER_H))
        dr = ImageDraw.Draw(fr)
        for cx, col in [(30, (244, 67, 54)), (70, (255, 214, 72)), (110, (56, 181, 119))]:
            dr.ellipse((cx - 13, 48 - 13, cx + 13, 48 + 13), fill=col, outline=INK, width=4)
        if "banner" in beat:
            # Banner text in the header bar, centred in the space
            # right of the dots; font shrinks until it fits. It never
            # covers the image below the header.
            size = 56
            while size > 20:
                fnt = font(size)
                bb = fnt.getbbox(beat["banner"])
                if bb[2] - bb[0] <= FRAME_W - 174:
                    break
                size -= 4
            draw_text_centred(dr, (150 + (FRAME_W - 24)) / 2, HEADER_H / 2,
                              beat["banner"], font(size), INK)
        browsers.append(fr)

    strip = ChipStrip(words, job.get("junctions", []))
    poses = job.get("poses") or [{"at": b["start"], "pose": POSES[i % len(POSES)]}
                                  for i, b in enumerate(beats)]

    def pose_at(t):
        p = poses[0]["pose"]
        for sw in poses:
            if t >= sw["at"]:
                p = sw["pose"]
        if p not in POSES:
            raise ValueError(f"unsupported pose: {p}")
        return p

    # Cut frames are integers: cut_frame = ceil(boundary x fps), first beat at frame 0.
    def beat_idx(frame_no, nframes):
        cuts = [0] + [math.ceil(beats[i]["end"] * FPS) for i in range(len(beats) - 1)] + [nframes]
        for i in range(len(beats)):
            if cuts[i] <= frame_no < cuts[i + 1]:
                return i
        return len(beats) - 1

    # Mascot rig (deduped visemes; original files untouched).
    out_dir = Path(args.out).parent if args.out else Path(args.stills or ".")
    out_dir.mkdir(parents=True, exist_ok=True)
    dedup_path = out_dir / "visemes-dedup.json"
    dedup_path.write_text(json.dumps(dedupe_visemes(visemes), ensure_ascii=False, indent=2) + "\n")
    rig = PoseMouthRig(ROOT / "assets" / "mascot" / "mouth_rig", str(voice),
                       str(dedup_path), str(job_dir / job["words"]))
    # NOTE: the old fixed canvas (cw/ch + per-pose offsets, top y1282)
    # was removed by the A-fixed change. Placement is now computed per
    # frame from the scaled rig frame's alpha bbox (see render_frame),
    # so no per-pose static offsets are needed.

    def render_frame(n, nframes):
        t = n / FPS
        bi = beat_idx(n, nframes)
        frame = bgs[bi].copy()
        frame.paste(browsers[bi], (FRAME_X, FRAME_Y))
        dr = ImageDraw.Draw(frame)
        dr.rounded_rectangle((FRAME_X, FRAME_Y, FRAME_X + FRAME_W, FRAME_Y + FRAME_H),
                             radius=28, outline=INK, width=6)
        widget_frame(frame, beats[bi], t)
        strip_im = strip.frame(t)
        frame.paste(strip_im, (0, CHIP_Y), strip_im)
        pose = pose_at(t + OFF)
        # A-fixed (approved 2026-11-05): scale the rig frame uniformly
        # by MASCOT_SCALE, then anchor its alpha bbox — centre on
        # x=540, bottom at MASCOT_BOTTOM_Y + bob. This keeps the
        # mascot centred at the bottom at the approved 1.2x size
        # regardless of pose or mouth shape, which both change the
        # frame's alpha bbox. The CTA anchor rule (1835 while a
        # below-mascot CTA pill is on screen) is applied just below.
        mfr = clean_alpha(rig.frame(pose, t))
        mfr = mfr.resize((max(1, round(mfr.width * MASCOT_SCALE)),
                          max(1, round(mfr.height * MASCOT_SCALE))),
                         Image.Resampling.LANCZOS)
        ab = mfr.split()[3].point(lambda v: 255 if v > 10 else 0).getbbox()
        bob = round(-BOB_PX * math.sin(2 * math.pi * t / 1.2))
        # CTA anchor rule (locked 2026-11-05, SPEC.md): while a
        # below-mascot CTA pill is on screen, raise the mascot's
        # bottom anchor from 1872 to 1835 so the pill never covers it.
        anchor = MASCOT_BOTTOM_Y
        for wdg in beats[bi].get("widgets", []):
            if wdg["type"] == "cta" and wdg.get("below_mascot") and wdg["start"] <= t < wdg["end"]:
                anchor = 1835
                break
        if ab is not None:
            frame.paste(mfr, (MASCOT_CENTRE_X - (ab[0] + ab[2]) // 2,
                              (anchor + bob) - ab[3]), mfr)
        cta_pill_frame(frame, beats[bi], t)
        return frame

    # Voice duration decides frame count, never a hardcoded duration.
    import wave as _wave
    with _wave.open(str(voice), "rb") as wav:
        dur = wav.getnframes() / wav.getframerate()
    nframes = round(dur * FPS)
    if args.max_frames is not None:
        nframes = min(nframes, args.max_frames)

    if args.stills:
        stills = Path(args.stills)
        stills.mkdir(parents=True, exist_ok=True)
        for label, n in [("start", round(0.5 * FPS)),
                         ("mid", nframes // 2),
                         ("end", max(0, nframes - 15))]:
            render_frame(min(n, nframes - 1), nframes).convert("RGB").save(stills / f"aot-{label}.png")
        print(f"stills: {stills} ({nframes} frames total at {dur:.2f}s voice)")
        return

    if not args.out:
        raise SystemExit("--out is required unless --stills is given")
    audio_path = mix_audio(job, job_dir, voice, out_dir)
    frames_dir = Path(args.frames_dir) if args.frames_dir else None
    if frames_dir:
        frames_dir.mkdir(parents=True, exist_ok=True)
    proc = None
    if frames_dir is None:
        cmd = ["ffmpeg", "-y", "-v", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
               "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-", "-i", audio_path,
               "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "18", "-preset", "medium",
               "-c:a", "aac", "-b:a", "192k", "-frames:v", str(nframes), str(args.out)]
        proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    try:
        for n in range(nframes):
            if frames_dir is not None:
                fp = frames_dir / f"{n:05d}.png"
                if fp.exists() and fp.stat().st_size > 0:
                    continue
                render_frame(n, nframes).convert("RGB").save(fp)
            else:
                proc.stdin.write(render_frame(n, nframes).convert("RGB").tobytes())
            if n % 300 == 0:
                print(f"frame {n}/{nframes}", flush=True)
    finally:
        if proc is not None:
            proc.stdin.close()
            proc.wait()
    if frames_dir is not None:
        subprocess.run(["ffmpeg", "-y", "-v", "error", "-framerate", str(FPS), "-i",
                        str(frames_dir / "%05d.png"), "-i", audio_path,
                        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "18", "-preset", "medium",
                        "-c:a", "aac", "-b:a", "192k", "-frames:v", str(nframes),
                        "-shortest", str(args.out)], check=True)
    print(f"done: {args.out} ({nframes} frames)")


if __name__ == "__main__":
    main()
