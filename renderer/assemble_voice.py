#!/usr/bin/env python3
"""Assemble ordered WAV voice segments with additive overlaps.

This tool is intentionally generic: it does not generate or transcribe audio.
It accepts uncompressed PCM or IEEE-float RIFF/WAVE segments and writes a
48 kHz mono IEEE-float WAV so additive overlap peaks are preserved without
normalization or clipping.
"""

import argparse
import json
import math
import struct
import sys
from pathlib import Path

import numpy as np


SAMPLE_RATE = 48_000
VOICE_WINDOW_MS = 25
VOICE_THRESHOLD_DB = -42.0
PRE_ROLL_SECONDS = 0.030
TAIL_WINDOW_MS = 10
TAIL_ACTIVE_DB = -35.0
TAIL_REBOUND_DB = 5.0
TAIL_SCAN_MS = 120
TAIL_FLOOR_DB = -52.0
TAIL_FLOOR_KEEP_MS = 20
FADE_IN_SECONDS = 0.020
DEFAULT_OVERLAP_SECONDS = 0.090
DEFAULT_TOPIC_OVERLAP_SECONDS = 0.050


def _read_wav(path):
    """Read uncompressed PCM/IEEE-float RIFF WAV samples as mono float32."""
    raw = Path(path).read_bytes()
    if len(raw) < 12 or raw[:4] != b"RIFF" or raw[8:12] != b"WAVE":
        raise ValueError(f"{path}: expected a little-endian RIFF/WAVE file")

    fmt = None
    audio_data = None
    offset = 12
    while offset + 8 <= len(raw):
        chunk_id = raw[offset:offset + 4]
        chunk_size = struct.unpack_from("<I", raw, offset + 4)[0]
        start = offset + 8
        end = start + chunk_size
        if end > len(raw):
            raise ValueError(f"{path}: truncated WAV chunk {chunk_id!r}")
        chunk = raw[start:end]
        if chunk_id == b"fmt ":
            fmt = chunk
        elif chunk_id == b"data" and audio_data is None:
            audio_data = chunk
        offset = end + (chunk_size & 1)

    if fmt is None or audio_data is None or len(fmt) < 16:
        raise ValueError(f"{path}: missing or invalid WAV fmt/data chunk")

    format_tag, channels, rate, _byte_rate, block_align, bits = struct.unpack_from("<HHIIHH", fmt)
    valid_bits = bits
    if format_tag == 0xFFFE:  # WAVE_FORMAT_EXTENSIBLE
        if len(fmt) < 40:
            raise ValueError(f"{path}: incomplete WAVE_FORMAT_EXTENSIBLE fmt chunk")
        valid_bits = struct.unpack_from("<H", fmt, 18)[0] or bits
        subformat = struct.unpack_from("<I", fmt, 24)[0]
        guid_tail = fmt[32:40]
        if fmt[24:32] not in (
            b"\x01\x00\x00\x00\x00\x00\x10\x00",
            b"\x03\x00\x00\x00\x00\x00\x10\x00",
        ) or guid_tail != b"\x80\x00\x00\xaa\x00\x38\x9b\x71":
            raise ValueError(f"{path}: unsupported extensible WAV subformat")
        format_tag = subformat

    if channels < 1 or rate < 1 or block_align < 1 or len(audio_data) % block_align:
        raise ValueError(f"{path}: invalid WAV channel/rate/frame layout")
    if bits % 8 or block_align != channels * (bits // 8):
        raise ValueError(f"{path}: unsupported WAV sample packing")
    if valid_bits < 1 or valid_bits > bits:
        raise ValueError(f"{path}: invalid valid-bits value for the WAV container bit depth")
    if format_tag == 3 and valid_bits != bits:
        raise ValueError(f"{path}: IEEE-float valid bits must match the WAV container bit depth")

    count = len(audio_data) // (bits // 8)
    if format_tag == 1:  # Integer PCM
        if bits == 8:
            integers = np.frombuffer(audio_data, dtype=np.uint8).astype(np.int32)
            integers >>= bits - valid_bits
            samples = (integers.astype(np.float32) - (1 << (valid_bits - 1))) / float(1 << (valid_bits - 1))
        elif bits == 16:
            integers = np.frombuffer(audio_data, dtype="<i2").astype(np.int32)
            integers >>= bits - valid_bits
            samples = integers.astype(np.float32) / float(1 << (valid_bits - 1))
        elif bits == 24:
            packed = np.frombuffer(audio_data, dtype=np.uint8).reshape(-1, 3).astype(np.int32)
            integers = packed[:, 0] | (packed[:, 1] << 8) | (packed[:, 2] << 16)
            integers[integers & 0x800000 != 0] -= 1 << 24
            integers >>= bits - valid_bits
            samples = integers.astype(np.float32) / float(1 << (valid_bits - 1))
        elif bits == 32:
            integers = np.frombuffer(audio_data, dtype="<i4").astype(np.int64)
            integers >>= bits - valid_bits
            samples = integers.astype(np.float32) / float(1 << (valid_bits - 1))
        else:
            raise ValueError(f"{path}: unsupported PCM width {bits} bits (use 8, 16, 24, or 32)")
    elif format_tag == 3:  # IEEE float
        if bits == 32:
            samples = np.frombuffer(audio_data, dtype="<f4").astype(np.float32, copy=False)
        elif bits == 64:
            samples = np.frombuffer(audio_data, dtype="<f8").astype(np.float32)
        else:
            raise ValueError(f"{path}: unsupported IEEE-float width {bits} bits (use 32 or 64)")
    else:
        raise ValueError(f"{path}: compressed or unsupported WAV format tag {format_tag}")

    if samples.size != count or not np.all(np.isfinite(samples)):
        raise ValueError(f"{path}: WAV contains invalid or non-finite samples")
    samples = samples.reshape(-1, channels)
    if channels > 1:
        samples = np.mean(samples, axis=1, dtype=np.float64).astype(np.float32)
    else:
        samples = samples[:, 0]

    if rate != SAMPLE_RATE and samples.size:
        target_count = max(1, round(samples.size * SAMPLE_RATE / rate))
        old_positions = np.arange(samples.size, dtype=np.float64)
        new_positions = np.arange(target_count, dtype=np.float64) * rate / SAMPLE_RATE
        samples = np.interp(new_positions, old_positions, samples).astype(np.float32)
    return samples


def _window_db(samples, window_ms):
    window = int(SAMPLE_RATE * window_ms / 1000)
    count = len(samples) // window
    if count == 0:
        return np.empty(0, dtype=np.float32)
    blocks = samples[:count * window].reshape(count, window)
    rms = np.sqrt(np.mean(blocks ** 2, axis=1) + 1e-12)
    return 20 * np.log10(rms + 1e-9)


def tail_end_idx(samples):
    """Return the decay-aware tail cut point, matching the source formula."""
    window = int(SAMPLE_RATE * TAIL_WINDOW_MS / 1000)
    count = len(samples) // window
    if count == 0:
        return len(samples), False
    blocks = samples[:count * window].reshape(count, window)
    rms = np.sqrt(np.mean(blocks ** 2, axis=1) + 1e-12)
    db = 20 * np.log10(rms + 1e-9)
    above = np.flatnonzero(db > TAIL_ACTIVE_DB)
    if len(above) == 0:
        return len(samples), False

    offset = int(above[-1])
    minimum = float(db[offset])
    minimum_index = offset
    truncated = False
    limit = min(count - 1, offset + TAIL_SCAN_MS // TAIL_WINDOW_MS)
    floor_index = None
    end_index = limit
    for index in range(offset + 1, limit + 1):
        if db[index] < minimum:
            minimum = float(db[index])
            minimum_index = index
        if db[index] > minimum + TAIL_REBOUND_DB:
            end_index = minimum_index
            truncated = True
            break
        if floor_index is None and db[index] <= TAIL_FLOOR_DB:
            floor_index = index
        if floor_index is not None and index >= floor_index + TAIL_FLOOR_KEEP_MS // TAIL_WINDOW_MS:
            end_index = floor_index + TAIL_FLOOR_KEEP_MS // TAIL_WINDOW_MS
            break
    else:
        if floor_index is not None:
            end_index = min(limit, floor_index + TAIL_FLOOR_KEEP_MS // TAIL_WINDOW_MS)
    return int((end_index + 1) * window), truncated


def _parse_script(path, segment_count):
    chunks = 0
    breaks = set()
    pending_break = False
    for line in Path(path).read_text(encoding="utf-8-sig").splitlines():
        if not line.strip():
            pending_break = True
            continue
        if pending_break and chunks:
            breaks.add(chunks + 1)  # 1-based index of the next segment
        chunks += 1
        pending_break = False
    if chunks != segment_count:
        raise ValueError(f"Script has {chunks} nonblank lines but {segment_count} audio segments were provided")
    return breaks


def _write_float_wav(path, samples):
    """Write mono 48 kHz IEEE-float WAV, preserving additive peaks."""
    data = np.asarray(samples, dtype="<f4").tobytes()
    if len(data) > 0xFFFFFFFF - 48:
        raise ValueError("Output is too large for a standard RIFF/WAVE file")
    riff_size = 48 + len(data)  # WAVE + fmt + fact + data chunks
    with Path(path).open("wb") as stream:
        stream.write(b"RIFF" + struct.pack("<I", riff_size) + b"WAVE")
        stream.write(b"fmt " + struct.pack("<IHHIIHH", 16, 3, 1, SAMPLE_RATE,
                                              SAMPLE_RATE * 4, 4, 32))
        stream.write(b"fact" + struct.pack("<II", 4, len(samples)))
        stream.write(b"data" + struct.pack("<I", len(data)) + data)


def _parse_args(argv=None):
    parser = argparse.ArgumentParser(
        description="Assemble ordered WAV voice segments with additive overlap and write a junction manifest."
    )
    parser.add_argument("segments", nargs="+", metavar="SEGMENT.wav",
                        help="audio chunks in final order")
    parser.add_argument("--script", help="one nonblank line per segment; blank lines mark topic breaks")
    parser.add_argument("--topic-break-before", "--topic-break", dest="topic_breaks", type=int,
                        action="append", default=[], metavar="INDEX",
                        help="mark a topic break before 1-based segment INDEX (repeat for multiple breaks)")
    parser.add_argument("--out", required=True, help="output 48 kHz mono WAV path")
    parser.add_argument("--overlap", type=float, default=DEFAULT_OVERLAP_SECONDS,
                        help=f"normal overlap in seconds (default: {DEFAULT_OVERLAP_SECONDS:.3f})")
    parser.add_argument("--topic-overlap", type=float, default=DEFAULT_TOPIC_OVERLAP_SECONDS,
                        help=f"topic-break overlap in seconds (default: {DEFAULT_TOPIC_OVERLAP_SECONDS:.3f})")
    return parser.parse_args(argv)


def main(argv=None):
    args = _parse_args(argv)
    if args.overlap < 0 or args.topic_overlap < 0:
        raise ValueError("Overlap durations must be zero or greater")

    segment_paths = [Path(p) for p in args.segments]
    for path in segment_paths:
        if not path.is_file():
            raise FileNotFoundError(f"Missing audio segment: {path}")
    output_path = Path(args.out)
    output_resolved = output_path.resolve()
    if any(output_resolved == path.resolve() for path in segment_paths):
        raise ValueError("Output path must not overwrite one of the input segments")

    topic_breaks = set(args.topic_breaks)
    if args.script:
        topic_breaks.update(_parse_script(args.script, len(segment_paths)))
    invalid = sorted(index for index in topic_breaks if index < 2 or index > len(segment_paths))
    if invalid:
        raise ValueError(f"Topic-break indexes must be before segments 2 through {len(segment_paths)}; invalid: {invalid}")

    segments = []
    for index, path in enumerate(segment_paths, 1):
        samples = _read_wav(path)
        windows_db = _window_db(samples, VOICE_WINDOW_MS)
        voiced = np.flatnonzero(windows_db > VOICE_THRESHOLD_DB)
        if len(voiced) == 0:
            raise ValueError(f"{path}: no complete {VOICE_WINDOW_MS} ms window exceeds {VOICE_THRESHOLD_DB:g} dB")
        start = max(0, int((int(voiced[0]) * VOICE_WINDOW_MS / 1000 - PRE_ROLL_SECONDS) * SAMPLE_RATE))
        end, truncated = tail_end_idx(samples)
        segment = samples[start:end].copy()
        if segment.size == 0:
            raise ValueError(f"{path}: trimming removed the entire segment")

        fade_in_samples = min(int(FADE_IN_SECONDS * SAMPLE_RATE), len(segment))
        segment[:fade_in_samples] *= np.linspace(0, 1, fade_in_samples)
        if truncated:
            print(f"{path}: decay tail rebound detected; cut at {end / SAMPLE_RATE:.3f}s", file=sys.stderr)
        segments.append(segment)

    overlaps = []
    for next_index in range(2, len(segments) + 1):
        seconds = args.topic_overlap if next_index in topic_breaks else args.overlap
        samples = int(seconds * SAMPLE_RATE)
        if samples >= len(segments[next_index - 2]):
            raise ValueError(f"Segment {next_index - 1} is not longer than its {seconds:.3f}s overlap")
        overlaps.append(samples)

    for index, overlap_samples in enumerate(overlaps):
        if overlap_samples:
            u = np.linspace(0, 1, overlap_samples)
            segments[index][-overlap_samples:] *= np.cos(u * math.pi / 2) ** 2

    total_samples = sum(len(segment) for segment in segments) - sum(overlaps)
    if total_samples <= 0:
        raise ValueError("Overlaps leave no output audio")
    output = np.zeros(total_samples, dtype=np.float32)
    position = 0
    onsets = {}
    for index, segment in enumerate(segments, 1):
        onsets[str(index)] = round(position / SAMPLE_RATE + PRE_ROLL_SECONDS, 3)
        output[position:position + len(segment)] += segment
        if index <= len(overlaps):
            position += len(segment) - overlaps[index - 1]

    output_path.parent.mkdir(parents=True, exist_ok=True)
    _write_float_wav(output_path, output)
    junctions_path = Path(str(output_path) + ".junctions.json")
    manifest = {
        "file": args.out,
        "onsets": onsets,
        "picks": {str(index): path.name for index, path in enumerate(segment_paths, 1)},
    }
    junctions_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"Assembled {len(segments)} segments -> {output_path}")
    print(f"Junctions -> {junctions_path}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError, struct.error) as exc:
        print(f"assemble_voice.py: error: {exc}", file=sys.stderr)
        raise SystemExit(2)
