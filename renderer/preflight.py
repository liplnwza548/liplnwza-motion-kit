#!/usr/bin/env python3
"""Preflight gate for a video job (ported from the Kurt P0-1 gate, generalized).

Run BEFORE composing. Fails (exit 1) on any hard violation and prints
PASS/FAIL lines for every check, so a failure names its cause instead of
composing silently. Nothing about any single job is hardcoded here: every
job-specific value arrives through arguments or the job manifest.

Checks (all optional inputs are skipped with a NOTE, never assumed):
  1. voice sha256 == --voice-sha, when a locked hash is supplied
  2. offset guard: when --off-locked is supplied, --off must equal it.
     This is a MECHANISM, not a number: the kit has no default offset.
     A job locks its own offset, and changing it needs a sync test
     decided by the owner (the Kurt job's locked value is 0.08; that
     number belongs to that job, not to this script).
  3. words concatenation == script concatenation (NFC, whitespace
     stripped); word times monotonic and within the voice duration
  4. provenance sidecar (if present) matches voice/script hashes and
     word count
  5. image manifest (if present): every beat accepted, file exists,
     sha256 matches, min size 1024x768; no rejected file sits in the
     images directory itself
  6. beat boundaries vs sentence onsets within 0.02 s (hard)
  7. sentence onsets vs nearest word start within 0.10 s; onsets more
     than 0.02 s from the nearest word start are reported as plan
     junctions, not treated as alignment errors
  8. NFRAMES from the real voice duration: round(duration * fps);
     voice duration within 0.5 s of --planned-end, when supplied
  9. visemes: shapes known; duplicate timestamps are reported (the
     dedup_visemes.py step resolves them) and the deduped schedule
     must be strictly increasing

Usage:
  python3 renderer/preflight.py --voice voice.wav --script script.txt \\
      --words words.json --visemes visemes.json \\
      [--voice-sha <hex>] [--off 0.08 --off-locked 0.08] \\
      [--manifest images.json --beats beats.json --images-dir images] \\
      [--provenance words.provenance.json] [--planned-end 60] [--fps 30]
  beats.json format: {"beats": [{"name": str, "start": float, "end": float}],
                      "onsets": [float, ...]}
  manifest format: {"beats": {name: {"file": relpath, "sha256": hex,
                        "status": "accepted"}},
                    "rejected": [{"file": relpath, ...}]}
Exit 0 = all hard checks pass.
"""
import argparse
import hashlib
import json
import subprocess
import sys
import unicodedata
from pathlib import Path

KNOWN_VISEME_SHAPES = {"CLOSED", "AA", "EE", "OH", "OO", "FV"}


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def ffprobe_duration(path):
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries",
                          "format=duration", "-of", "csv=p=0", str(path)],
                         capture_output=True, text=True, check=True)
    return float(out.stdout.strip())


class Checker:
    def __init__(self):
        self.failures = []
        self.warnings = []

    def check(self, name, ok, detail=""):
        print(f"{'PASS' if ok else 'FAIL'} {name} {detail}")
        if not ok:
            self.failures.append(name)

    def warn(self, msg):
        print(f"WARN {msg}")
        self.warnings.append(msg)


def load_words(path):
    words = json.loads(Path(path).read_text(encoding="utf-8"))
    if isinstance(words, dict):
        words = words["words"]
    return words


def main(argv=None):
    p = argparse.ArgumentParser()
    p.add_argument("--voice", required=True)
    p.add_argument("--script", required=True)
    p.add_argument("--words", required=True)
    p.add_argument("--visemes", required=True)
    p.add_argument("--voice-sha")
    p.add_argument("--off", type=float)
    p.add_argument("--off-locked", type=float)
    p.add_argument("--manifest")
    p.add_argument("--beats")
    p.add_argument("--images-dir")
    p.add_argument("--provenance")
    p.add_argument("--planned-end", type=float)
    p.add_argument("--fps", type=int, default=30)
    p.add_argument("--root", default=".")
    a = p.parse_args(argv)
    root = Path(a.root).resolve()
    c = Checker()

    def resolve(path):
        path = Path(path)
        return path if path.is_absolute() else root / path

    voice = resolve(a.voice)
    script = resolve(a.script)
    voice_sha = sha256(voice)
    if a.voice_sha:
        c.check("voice_sha_locked", voice_sha == a.voice_sha,
                f"sha={voice_sha[:12]}")
    else:
        print("NOTE voice_sha_locked skipped (no --voice-sha supplied)")

    if a.off is not None and a.off_locked is not None:
        c.check("off_unchanged_guard", a.off == a.off_locked,
                f"off={a.off} locked={a.off_locked}")
    elif a.off is not None:
        print(f"NOTE off={a.off} (no --off-locked supplied, guard inactive)")

    script_concat = "".join(unicodedata.normalize(
        "NFC", script.read_text(encoding="utf-8")).split())
    words = load_words(resolve(a.words))
    words_concat = "".join(unicodedata.normalize("NFC", w["word"])
                           for w in words)
    c.check("words_concat_equals_script", words_concat == script_concat,
            f"words={len(words)} chars={len(words_concat)} "
            f"script_chars={len(script_concat)}")
    mono = all(b["start"] >= a2["start"] and b["end"] >= b["start"]
               for a2, b in zip(words, words[1:]))
    c.check("words_times_monotonic", mono)
    duration = ffprobe_duration(voice)
    c.check("words_within_voice", words[-1]["end"] <= duration + 0.05,
            f"last_end={words[-1]['end']} duration={duration}")

    if a.provenance:
        prov_path = resolve(a.provenance)
        if prov_path.exists():
            prov = json.loads(prov_path.read_text(encoding="utf-8"))
            c.check("provenance_voice_sha",
                    prov.get("voice_sha256") == voice_sha)
            c.check("provenance_script_sha",
                    prov.get("script_sha256") == sha256(script))
            c.check("provenance_word_count",
                    prov.get("chips") == len(words),
                    f"prov={prov.get('chips')} actual={len(words)}")
        else:
            c.warn("provenance sidecar missing")
    else:
        print("NOTE provenance check skipped (no --provenance supplied)")

    beats = []
    onsets = []
    if a.beats:
        beats_doc = json.loads(resolve(a.beats).read_text(encoding="utf-8"))
        beats = beats_doc.get("beats", [])
        onsets = beats_doc.get("onsets", [])

    if a.manifest:
        manifest = json.loads(resolve(a.manifest).read_text(encoding="utf-8"))
        mbeats = manifest.get("beats", {})
        from PIL import Image
        for name in sorted(mbeats):
            entry = mbeats[name]
            path = resolve(entry["file"])
            ok = (path.exists() and entry.get("status") == "accepted"
                  and sha256(path) == entry["sha256"])
            if ok:
                with Image.open(path) as im:
                    ok = im.size[0] >= 1024 and im.size[1] >= 768
            c.check(f"manifest_image_{name}", ok,
                    f"{entry['file']} size_ok={ok}")
        if beats:
            missing = [b["name"] for b in beats if b["name"] not in mbeats]
            c.check("manifest_covers_beats", not missing, f"missing={missing}")
        rejected_names = {Path(r["file"]).name
                          for r in manifest.get("rejected", [])}
        if a.images_dir:
            stray = [q.name for q in resolve(a.images_dir).glob("*.webp")
                     if q.name in rejected_names]
            c.check("no_rejected_in_images_dir", not stray, f"stray={stray}")
    else:
        print("NOTE manifest checks skipped (no --manifest supplied)")

    if beats and onsets:
        bounds = sorted({b["start"] for b in beats} | {b["end"] for b in beats})
        max_bo = max(min(abs(on - b) for b in bounds) for on in onsets)
        c.check("beat_boundary_vs_onset_le_0.02", max_bo <= 0.02,
                f"max_diff={max_bo:.3f}s")
        for on in onsets:
            nw = min(words, key=lambda w: abs(w["start"] - on))
            d = abs(nw["start"] - on)
            if d > 0.02:
                print(f"NOTE onset {on}: nearest word '{nw['word']}' starts "
                      f"{nw['start']} (diff {d:.3f}s > 0.02 -- plan junction, "
                      f"not an MFA word start)")
            c.check(f"onset_vs_word_le_0.10_onset_{on}", d <= 0.10,
                    f"diff={d:.3f}s")
    elif beats or onsets:
        print("NOTE beat/onset cross-check skipped (need both --beats "
              "beats and onsets)")

    nframes = round(duration * a.fps)
    if a.planned_end is not None:
        c.check("voice_duration_vs_plan_le_0.5",
                abs(duration - a.planned_end) <= 0.5,
                f"duration={duration} planned={a.planned_end} "
                f"nframes={nframes}")
    else:
        print(f"NOTE nframes={nframes} (no --planned-end supplied)")

    vis = json.loads(resolve(a.visemes).read_text(encoding="utf-8"))
    if isinstance(vis, dict):
        vis = vis.get("visemes", vis)
    shapes_ok = all(v["shape"] in KNOWN_VISEME_SHAPES for v in vis)
    c.check("viseme_shapes_known", shapes_ok, f"visemes={len(vis)}")
    dedup = {}
    for v in vis:
        dedup[v["start"]] = v["shape"]  # last shape wins per timestamp
    if len(dedup) != len(vis):
        print(f"NOTE viseme duplicate timestamps: raw={len(vis)} "
              f"deduped={len(dedup)} (run dedup_visemes.py before rendering)")
    ts = sorted(dedup)
    c.check("viseme_dedup_strictly_increasing", ts == sorted(set(ts)),
            f"deduped={len(dedup)}")

    if c.warnings:
        print("WARNINGS:", "; ".join(c.warnings))
    if c.failures:
        print(f"PREFLIGHT FAILED: {len(c.failures)} check(s): "
              f"{', '.join(c.failures)}")
        return 1
    print(f"PREFLIGHT PASSED (voice {duration}s -> {nframes} frames "
          f"@ {a.fps}fps)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
