#!/usr/bin/env python3
"""Frame-content QC for a composed clip (ported from the Kurt P0-3 QC, generalized).

This is a different layer from renderer/kit.py qc(), which checks
container/codec/loudness: this script checks that the PICTURE actually
changes at the right frames. Nothing about any single job is hardcoded:
beats, manifest, panel geometry and expected duration/frames all arrive
through arguments.

Rules that must not be regressed:
  * Frames are extracted BY INDEX (ffmpeg select filter) -- never by
    time. Time-based extraction (-ss, either side of -i) is banned:
    rounding a frame timestamp to 4 decimals can push it past the
    frame's own pts (e.g. frame 77 pts 2.566667 vs -ss 2.5667 returns
    frame 78 instead), which once produced fake 0.00 cut diffs.
  * Cut frames come from cut_frame = ceil(boundary * fps), and 3
    frames are examined per cut (cut-1 / cut / cut+1).
  * Panels are cover-cropped from the manifest with the same
    center-crop algorithm as the compositor, so comparison is against
    what the clip should show, not the un-cropped source image.

Checks:
  1. duration within +/-0.05 s of expected, frame count exact (ffprobe)
  2. every internal beat cut: panel region changes at `cut`
     (mean abs diff cut-1 -> cut > threshold) and is stable at cut+1
     (< stable threshold)
  3. frame 0's image region best-matches the first beat's panel
  4. each beat's mid-frame image region best-matches that beat's panel

beats.json format: {"beats": [{"name": str, "start": float, "end": float,
                                "image": manifest_key}]}
manifest format: {"beats": {key: {"file": relpath, "sha256": hex,
                                   "status": "accepted"}}}
Paths in the manifest are resolved against --root.

Usage:
  python3 tests/qc.py --video clip.mp4 --beats beats.json --manifest images.json \\
      --root JOBDIR --duration 60 --frames 1800 [--fps 30] \\
      [--panel-box 48,48,1032,928] [--img-box 48,144,1032,928] \\
      [--panel-size 984,784]
Exit 0 only if every check passes; prints measured values for all cuts.
"""
import argparse
import json
import math
import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np
from PIL import Image


def cover_crop(im, tw, th):
    w, h = im.size
    s = max(tw / w, th / h)
    im2 = im.convert("RGB").resize((round(w * s), round(h * s)), Image.Resampling.LANCZOS)
    x = (im2.width - tw) // 2
    y = (im2.height - th) // 2
    return im2.crop((x, y, x + tw, y + th))


def extract_frame(video, frame_no, tmp):
    out = tmp / f"f{frame_no}.png"
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", str(video),
                    "-vf", f"select='eq(n\\,{frame_no})'",
                    "-frames:v", "1", str(out)], check=True)
    return Image.open(out).convert("RGB")


def mean_abs_diff(a, b):
    return float(np.abs(np.asarray(a, dtype=np.int16)
                        - np.asarray(b, dtype=np.int16)).mean())


def parse_box(s):
    x0, y0, x1, y1 = (int(v) for v in s.split(","))
    return (x0, y0, x1, y1)


def main(argv=None):
    p = argparse.ArgumentParser()
    p.add_argument("--video", required=True)
    p.add_argument("--beats", required=True)
    p.add_argument("--manifest", required=True)
    p.add_argument("--root", default=".")
    p.add_argument("--duration", type=float, required=True)
    p.add_argument("--frames", type=int, required=True)
    p.add_argument("--fps", type=int, default=30)
    p.add_argument("--panel-box", default="48,48,1032,928")
    p.add_argument("--img-box", default="48,144,1032,928")
    p.add_argument("--panel-size", default="984,784")
    p.add_argument("--change-threshold", type=float, default=10)
    p.add_argument("--stable-threshold", type=float, default=5)
    a = p.parse_args(argv)
    root = Path(a.root).resolve()
    video = Path(a.video)
    panel_box = parse_box(a.panel_box)
    img_box = parse_box(a.img_box)
    pw, ph = (int(v) for v in a.panel_size.split(","))

    beats = json.loads(Path(a.beats).read_text(encoding="utf-8"))["beats"]
    manifest = json.loads(Path(a.manifest).read_text(encoding="utf-8"))["beats"]

    probe = json.loads(subprocess.run(
        ["ffprobe", "-v", "quiet", "-print_format", "json", "-show_format", "-show_streams",
         str(video)], capture_output=True, text=True, check=True).stdout)
    duration = float(probe["format"]["duration"])
    vstream = next(s for s in probe["streams"] if s["codec_type"] == "video")
    frames = int(vstream.get("nb_frames", 0) or 0)
    failures = []
    print(f"duration={duration:.3f} (expected {a.duration} +/-0.05) frames={frames} (expected {a.frames})")
    if abs(duration - a.duration) > 0.05:
        failures.append("duration")
    if frames != a.frames:
        failures.append("frame_count")

    panels = {}
    for b in beats:
        key = b.get("image", b["name"])
        entry = manifest[key]
        panels[b["name"]] = cover_crop(Image.open(root / entry["file"]), pw, ph)

    def best_match(crop):
        small = crop.resize((246, 196), Image.Resampling.BILINEAR)
        scored = [(mean_abs_diff(small, panel.resize((246, 196), Image.Resampling.BILINEAR)), name)
                  for name, panel in panels.items()]
        scored.sort()
        return scored[0]

    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        first = beats[0]["name"]
        crop0 = extract_frame(video, 0, tmp).crop(img_box)
        diff0, beat0 = best_match(crop0)
        print(f"frame0 best_match={beat0} diff={diff0:.2f} (must be {first})")
        if beat0 != first:
            failures.append("frame0_not_first_beat")

        cuts_ok = 0
        for i in range(len(beats) - 1):
            boundary = beats[i]["end"]
            cut = math.ceil(boundary * a.fps)
            prev = extract_frame(video, cut - 1, tmp).crop(panel_box)
            cur = extract_frame(video, cut, tmp).crop(panel_box)
            nxt = extract_frame(video, cut + 1, tmp).crop(panel_box)
            d_change = mean_abs_diff(prev, cur)
            d_stable = mean_abs_diff(cur, nxt)
            ok = d_change > a.change_threshold and d_stable < a.stable_threshold
            cuts_ok += ok
            print(f"cut@{boundary:.2f}s frame={cut} change={d_change:.2f} (>{a.change_threshold}) "
                  f"stable={d_stable:.2f} (<{a.stable_threshold}) {'OK' if ok else 'FAIL'}")
            if not ok:
                failures.append(f"cut_{boundary}")
        mid_ok = 0
        for b in beats:
            mid = (math.ceil(b["start"] * a.fps) + math.ceil(b["end"] * a.fps)) // 2
            crop = extract_frame(video, mid, tmp).crop(img_box)
            diff, beat = best_match(crop)
            ok = beat == b["name"]
            mid_ok += ok
            print(f"mid-beat {b['name']} frame={mid} best_match={beat} diff={diff:.2f} {'OK' if ok else 'FAIL'}")
            if not ok:
                failures.append(f"mid_{b['name']}")
        print(f"cuts {cuts_ok}/{len(beats) - 1} mid-beats {mid_ok}/{len(beats)}")
    if failures:
        print(f"QC FAILED: {failures}")
        return 1
    print("QC PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
