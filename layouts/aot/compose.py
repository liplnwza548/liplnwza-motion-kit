#!/usr/bin/env python3
"""Generic AoT-layout compositor (PIL frames + ffmpeg, no AI video).

Layout (locked 2026-11-02, see SPEC.md in this folder):
  1080x1920, 30fps, bg #FFF6E8 with dot grid
  top:    frame x48..1032, y48..928 (header #FFE9A8 96px + image
          centre-crop cover 984x784, hard cuts at beat boundaries,
          no zoom/pan/overlay)
  chips:  strip y915..1255, paper chips, Prompt-Bold, palette
          yellow/blue/red/green, max 3 words per row, pop 0.14s
  mascot: PoseMouthRig frames (master lock + rig only, from
          assets/mascot/mouth_rig/), centred, top y1282 before bob,
          bob amplitude 7px, so the chips/mascot gap stays >= 20px

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
MASCOT_Y = 1282
BOB_PX = 7
assert MASCOT_Y - BOB_PX - (CHIP_Y + CHIP_H) >= 20, "chips/mascot zones overlap"
BG = (255, 246, 232)
HEADER = (255, 233, 168)
INK = (24, 27, 38)
PALETTE = [(255, 214, 72), (34, 100, 216), (244, 67, 54), (56, 181, 119)]
PALETTE_TEXT = [(24, 27, 38), (255, 253, 246), (255, 253, 246), (24, 27, 38)]
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


def pop(u):
    """Back-out overshoot pop, 0 at u<=0, 1 at u>=1 (same curve as paper chips)."""
    if u <= 0:
        return 0
    u = min(1, u)
    return 1 + 2.70158 * (u - 1) ** 3 + 1.70158 * (u - 1) ** 2


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
                key = (ri, wi, width)
                if key not in self._base:
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
                elif t < w["start"] + OFF + 0.14:
                    s = pop((t - w["start"] - OFF) / 0.14)
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
    # Background: cream + dot grid (dots only below the top frame, as in the proven layout).
    bg = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(bg)
    for yy in range(980, H, 56):
        for xx in range(56, W, 56):
            d.ellipse((xx - 2, yy - 2, xx + 2, yy + 2), fill=(190, 180, 160))

    # Top panels, pre-cropped to the image area 984x784.
    panels = []
    for beat in beats:
        entry = job["images"][beat["name"]]
        panels.append(cover_crop(Image.open(job_dir / entry["file"]), IMG_W, IMG_H))
    browsers = []
    for pimg in panels:
        fr = Image.new("RGB", (FRAME_W, FRAME_H), HEADER)
        fr.paste(pimg, (0, HEADER_H))
        dr = ImageDraw.Draw(fr)
        for cx, col in [(30, (244, 67, 54)), (70, (255, 214, 72)), (110, (56, 181, 119))]:
            dr.ellipse((cx - 13, 48 - 13, cx + 13, 48 + 13), fill=col, outline=INK, width=4)
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
    statics, sizes = {}, []
    for pose in dict.fromkeys([s["pose"] for s in poses]):
        f = rig.static_frame(pose, "CLOSED")
        statics[pose] = f
        sizes.append(f.size)
    cw = max(w for w, _ in sizes) + 48
    ch = max(h for _, h in sizes) + 48
    offsets = {}
    for pose, f in statics.items():
        cf = clean_alpha(f)
        bbox = cf.split()[3].point(lambda p: 255 if p > 10 else 0).getbbox()
        left, _u, right, lower = bbox
        offsets[pose] = (cw // 2 - (left + right) // 2, (ch - 12) - lower)

    def render_frame(n, nframes):
        t = n / FPS
        frame = bg.copy()
        frame.paste(browsers[beat_idx(n, nframes)], (FRAME_X, FRAME_Y))
        dr = ImageDraw.Draw(frame)
        dr.rounded_rectangle((FRAME_X, FRAME_Y, FRAME_X + FRAME_W, FRAME_Y + FRAME_H),
                             radius=28, outline=INK, width=6)
        strip_im = strip.frame(t)
        frame.paste(strip_im, (0, CHIP_Y), strip_im)
        pose = pose_at(t + OFF)
        mfr = clean_alpha(rig.frame(pose, t))
        canvas = Image.new("RGBA", (cw, ch), (0, 0, 0, 0))
        canvas.paste(mfr, offsets[pose], mfr)
        bob = round(-BOB_PX * math.sin(2 * math.pi * t / 1.2))
        frame.paste(canvas, ((W - cw) // 2, MASCOT_Y + bob), canvas)
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
    frames_dir = Path(args.frames_dir) if args.frames_dir else None
    if frames_dir:
        frames_dir.mkdir(parents=True, exist_ok=True)
    proc = None
    if frames_dir is None:
        cmd = ["ffmpeg", "-y", "-v", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
               "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-", "-i", str(voice),
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
                        str(frames_dir / "%05d.png"), "-i", str(voice),
                        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "18", "-preset", "medium",
                        "-c:a", "aac", "-b:a", "192k", "-frames:v", str(nframes),
                        "-shortest", str(args.out)], check=True)
    print(f"done: {args.out} ({nframes} frames)")


if __name__ == "__main__":
    main()
