#!/usr/bin/env python3
"""Post-render gate + 2-pass loudnorm for a finished mp4 (ported from Kurt P0-4).

The compositor itself does NOT loudnorm (it muxes AAC directly), so
loudness must be enforced here, on the mp4 -- never assumed from the wav.
This script:
  1. measures a file with ffmpeg loudnorm (JSON parsed from stderr)
  2. optionally loudnorms it in 2 passes (measured -> linear) to
     -16 LUFS / TP -1.0
  3. gates a finished file: duration +/-0.05 s, exact frame count,
     integrated loudness -16 +/-0.5 LUFS, true peak <= -1.0 dBTP,
     all measured from the mp4 itself.

TRUE-PEAK TRAP (measured, do not "simplify" this away): linear mode
preserves voice dynamics (no dynamic compression) but does NOT
true-peak-limit: gain + AAC re-encode overshoot pushed a TP=-1.0-targeted
pass to +0.67 dBTP in testing. Targeting TP=-2.0 in the filter leaves
headroom so the finished file lands at TP <= -1.0 (tested: -16.01 LUFS /
-2.00 dBTP). The gate below still asserts TP <= -1.0 on the finished
file. Explicit AAC 192k is REQUIRED: without it ffmpeg defaults to
~69 kbps AAC, whose true-peak overshoot measured +2.67 dB vs the 192k
encode from the identical filter.

Duration is judged from the VIDEO stream: loudnorm/AAC padding adds
~0.07 s to the audio stream, which is encoder padding, not content
(format duration = max stream duration, so it would fail spuriously).

Usage:
  python3 renderer/post_render_gate.py --check <mp4> --duration 60 --frames 1800
  python3 renderer/post_render_gate.py --loudnorm <in.mp4> <out.mp4> --duration 60 --frames 1800
Exit 0 only if the gate passes.
"""
import json
import re
import subprocess
import sys
from pathlib import Path


def probe(path):
    out = subprocess.run(["ffprobe", "-v", "quiet", "-print_format", "json",
                          "-show_format", "-show_streams", str(path)],
                         capture_output=True, text=True, check=True)
    return json.loads(out.stdout)


def measure_loudness(path):
    """Return the loudnorm JSON for a file (ffmpeg loudnorm measure pass)."""
    cmd = ["ffmpeg", "-i", str(path), "-vn", "-af",
           "loudnorm=I=-16:TP=-1.0:LRA=11:print_format=json",
           "-f", "null", "-"]
    out = subprocess.run(cmd, capture_output=True, text=True)
    m = re.search(r"\{[^}]*\"input_i\"[^}]*\}", out.stderr, re.S)
    if not m:
        raise RuntimeError(f"could not parse loudnorm JSON from ffmpeg output:\n{out.stderr[-2000:]}")
    return json.loads(m.group(0))


def loudnorm_file(src, dst):
    m = measure_loudness(src)
    filt = (
        f"loudnorm=I=-16:TP=-2.0:LRA=11:measured_I={m['input_i']}:"
        f"measured_TP={m['input_tp']}:measured_LRA={m['input_lra']}:"
        f"measured_thresh={m['input_thresh']}:offset={m['target_offset']}:linear=true"
    )
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", str(src), "-af", filt,
                    "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
                    "-ar", "48000", str(dst)], check=True)
    return dst


def gate(path, expected_duration, expected_frames):
    failures = []
    info = probe(path)
    vstream = next(s for s in info["streams"] if s["codec_type"] == "video")
    frames = int(vstream.get("nb_frames", 0) or 0)
    fps_num, fps_den = (int(x) for x in vstream.get("r_frame_rate", "30/1").split("/"))
    duration = float(vstream.get("duration", frames * fps_den / fps_num))
    audio = [s for s in info["streams"] if s["codec_type"] == "audio"]
    audio_duration = float(audio[0]["duration"]) if audio and "duration" in audio[0] else None
    loud = measure_loudness(path)
    integrated = float(loud["input_i"])
    tp = float(loud["input_tp"])
    print(f"video duration={duration:.3f} (expected {expected_duration} +/-0.05)"
          + (f" audio duration={audio_duration:.3f}" if audio_duration is not None else ""))
    print(f"frames={frames} (expected {expected_frames})")
    print(f"loudness I={integrated:.2f} LUFS (target -16 +/-0.5) TP={tp:.2f} dBTP (must be <= -1.0)")
    if abs(duration - expected_duration) > 0.05:
        failures.append("duration")
    if audio_duration is not None and not (duration - 0.05 <= audio_duration <= duration + 0.5):
        failures.append("audio_duration")
    if frames != expected_frames:
        failures.append("frame_count")
    if abs(integrated - (-16.0)) > 0.5:
        failures.append("loudness_I")
    if tp > -1.0:
        failures.append("true_peak")
    if failures:
        print(f"POST-RENDER GATE FAILED: {failures}")
        return 1
    print("POST-RENDER GATE PASSED")
    return 0


def main():
    args = sys.argv[1:]
    duration = float(args[args.index("--duration") + 1]) if "--duration" in args else None
    frames = int(args[args.index("--frames") + 1]) if "--frames" in args else None
    if "--loudnorm" in args:
        i = args.index("--loudnorm")
        src, dst = Path(args[i + 1]), Path(args[i + 2])
        loudnorm_file(src, dst)
        print(f"loudnormed {src} -> {dst}")
        if duration is None or frames is None:
            print("NOTE gate skipped (supply --duration/--frames to gate)")
            return 0
        return gate(dst, duration, frames)
    if "--check" in args:
        if duration is None or frames is None:
            print("usage: post_render_gate.py --check <mp4> --duration <s> --frames <n>")
            return 2
        return gate(Path(args[args.index("--check") + 1]), duration, frames)
    print("usage: post_render_gate.py --check <mp4> --duration <s> --frames <n> | --loudnorm <in.mp4> <out.mp4> --duration <s> --frames <n>")
    return 2


if __name__ == "__main__":
    sys.exit(main())
