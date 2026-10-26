"""Validated optional BGM preparation and FFmpeg mix graph for the kit renderer."""
from __future__ import annotations

import json
import math
import shutil
import subprocess
import wave
from pathlib import Path

import numpy as np


TARGET_LUFS = -16.0
TRUE_PEAK_DBTP = -1.0
MIN_BGM_DUCK_DB = 12.0
FADE_IN_SECONDS = 0.5
FADE_OUT_SECONDS = 1.5


def _finite_number(value, field: str, *, minimum: float = 0.0) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"BGM {field} must be a number")
    value = float(value)
    if not math.isfinite(value) or value < minimum:
        raise ValueError(f"BGM {field} must be finite and >= {minimum}")
    return value


def validate_bgm(job: dict, job_dir: Path, duration: float) -> dict | None:
    """Fail closed unless an optional, job-local, rights-cleared track is approved."""
    bgm = job.get("bgm")
    if bgm is None:
        return None
    if not isinstance(bgm, dict) or set(bgm) - {
        "source_id", "path", "in_s", "gain_db", "loop", "fade_in_s", "fade_out_s", "ducking",
    }:
        raise ValueError("BGM has unsupported fields")
    source_id = bgm.get("source_id")
    if not isinstance(source_id, str) or not source_id.strip():
        raise ValueError("BGM source_id is required")
    relative = bgm.get("path")
    if not isinstance(relative, str) or not relative:
        raise ValueError("BGM path is required")
    relative_path = Path(relative)
    if relative_path.is_absolute() or ".." in relative_path.parts:
        raise ValueError("BGM path must stay inside the job folder")
    job_root = Path(job_dir).resolve()
    path = (job_root / relative_path).resolve()
    if not path.is_relative_to(job_root) or not path.is_file():
        raise ValueError("BGM file is missing or outside the job folder")

    matches = [source for source in job.get("sources", [])
               if isinstance(source, dict) and source.get("id") == source_id]
    if len(matches) != 1:
        raise ValueError(f"BGM source_id {source_id!r} must resolve to exactly one source")
    source = matches[0]
    if not all(isinstance(source.get(key), str) and source[key].strip()
               for key in ("origin", "creator", "license", "usage", "checked_date")):
        raise ValueError("BGM source is missing origin, creator, license, usage, or checked_date")
    rights = source.get("rights")
    if not isinstance(rights, dict) or rights.get("status") != "cleared" or not all(
        isinstance(rights.get(key), str) and rights[key].strip()
        for key in ("evidence", "checked_date")
    ):
        raise ValueError("BGM rights are incomplete; require rights.status=cleared and evidence")
    source_approval = source.get("approval")
    if not isinstance(source_approval, dict) or source_approval.get("status") != "approved" or source_approval.get("approved_by") != "Philip" or not isinstance(source_approval.get("evidence"), str) or not source_approval["evidence"].strip():
        raise ValueError("BGM source is not approved by Philip with recorded evidence")

    in_s = _finite_number(bgm.get("in_s", 0), "in_s")
    gain_db = bgm.get("gain_db", -22.0)
    if isinstance(gain_db, bool) or not isinstance(gain_db, (int, float)) or not math.isfinite(float(gain_db)):
        raise ValueError("BGM gain_db must be a finite number")
    gain_db = float(gain_db)
    if not -60.0 <= gain_db <= -12.0:
        raise ValueError("BGM gain_db must be between -60 and -12 dB after stem normalization")
    if bgm.get("loop", False) is not False:
        raise ValueError("BGM looping is not supported; provide a track long enough for the job")
    for field, expected in (("fade_in_s", FADE_IN_SECONDS), ("fade_out_s", FADE_OUT_SECONDS)):
        if field in bgm:
            value = _finite_number(bgm[field], field)
            if not math.isclose(value, expected, rel_tol=0.0, abs_tol=1e-9):
                raise ValueError(f"BGM {field} is fixed at {expected:.1f} seconds")
    if bgm.get("ducking", True) is not True:
        raise ValueError("BGM ducking cannot be disabled")

    ffprobe = shutil.which("ffprobe")
    if not ffprobe:
        raise ValueError("ffprobe is required to verify BGM duration")
    result = subprocess.run(
        [ffprobe, "-v", "error", "-show_format", "-of", "json", str(path)],
        check=True, capture_output=True, text=True,
    )
    try:
        source_duration = float(json.loads(result.stdout)["format"]["duration"])
    except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
        raise ValueError("Unable to read BGM source duration") from exc
    if in_s + float(duration) > source_duration + 0.02:
        raise ValueError("BGM is shorter than the requested job duration; looping is disabled")
    return {"path": path, "source_id": source_id, "in_s": in_s, "gain_db": gain_db,
            "source_duration": source_duration}


def prepare_bgm_stem(bgm: dict | None, duration: float, output_path: Path) -> Path | None:
    """Decode the selected track to a job-length PCM stem without looping it."""
    if bgm is None:
        return None
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run([
        "ffmpeg", "-y", "-v", "error", "-ss", f"{bgm['in_s']:.6f}", "-i", str(bgm["path"]),
        "-t", f"{float(duration):.6f}", "-ar", "48000", "-ac", "2", "-c:a", "pcm_s16le",
        str(output_path),
    ], check=True)
    return output_path


def normalize_stem(source_path: Path, output_path: Path, duration: float) -> Path:
    """Normalize one audio stem to -16 LUFS / -1 dBTP before any mix."""
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run([
        "ffmpeg", "-y", "-v", "error", "-i", str(source_path), "-af",
        f"loudnorm=I={TARGET_LUFS}:TP={TRUE_PEAK_DBTP}:LRA=7", "-t", f"{float(duration):.6f}",
        "-ar", "48000", "-ac", "2", "-c:a", "pcm_s16le", str(output_path),
    ], check=True)
    return output_path


def _read_pcm(path: Path) -> tuple[np.ndarray, int]:
    with wave.open(str(path), "rb") as source:
        if source.getsampwidth() != 2:
            raise ValueError(f"Expected 16-bit PCM stem: {path}")
        channels = source.getnchannels()
        rate = source.getframerate()
        samples = np.frombuffer(source.readframes(source.getnframes()), dtype="<i2")
    if channels < 1 or samples.size % channels:
        raise ValueError(f"Invalid PCM stem shape: {path}")
    return samples.reshape(-1, channels).astype(np.float64) / 32768.0, rate


def safe_bgm_gain(voice_path: Path, bgm_path: Path, requested_gain_db: float,
                  *, min_duck_db: float = MIN_BGM_DUCK_DB, window_seconds: float = 0.4,
                  hop_seconds: float = 0.1, silence_dbfs: float = -60.0) -> tuple[float, dict]:
    """Choose one bed gain that meets the duck floor in each active 0.4s window."""
    voice, voice_rate = _read_pcm(voice_path)
    bgm, bgm_rate = _read_pcm(bgm_path)
    if voice_rate != bgm_rate:
        raise ValueError("Normalized voice and BGM stems must use the same sample rate")
    rate = voice_rate
    window = max(1, round(window_seconds * rate))
    hop = max(1, round(hop_seconds * rate))
    active_floor = 10 ** (silence_dbfs / 20.0)
    epsilon = 1e-12
    requested = float(requested_gain_db)
    effective = requested
    margins = []
    for start in range(0, max(1, len(voice) - window + 1), hop):
        end = min(len(voice), start + window)
        voice_rms = float(np.sqrt(np.mean(voice[start:end] ** 2)))
        if voice_rms < active_floor:
            continue
        bgm_slice = bgm[start:min(end, len(bgm))]
        if not len(bgm_slice):
            continue
        bgm_rms = float(np.sqrt(np.mean(bgm_slice ** 2)))
        if bgm_rms <= epsilon:
            continue
        limit_gain = 20 * math.log10((voice_rms * 10 ** (-(min_duck_db + 0.25) / 20.0)) / bgm_rms)
        effective = min(effective, limit_gain)
    if effective < -60.0:
        raise ValueError("BGM cannot stay 12 dB below the normalized voice without muting; omit BGM")
    gain = 10 ** (effective / 20.0)
    for start in range(0, max(1, len(voice) - window + 1), hop):
        end = min(len(voice), start + window)
        voice_rms = float(np.sqrt(np.mean(voice[start:end] ** 2)))
        if voice_rms < active_floor:
            continue
        bgm_slice = bgm[start:min(end, len(bgm))]
        if not len(bgm_slice):
            continue
        bgm_rms = float(np.sqrt(np.mean(bgm_slice ** 2))) * gain
        if bgm_rms <= epsilon:
            margins.append(float("inf"))
        else:
            margins.append(20 * math.log10(voice_rms / bgm_rms))
    if margins and min(margins) + 1e-6 < min_duck_db:
        raise ValueError("Unable to meet the 12 dB BGM duck floor in active voice windows")
    return effective, {
        "analysis_window_seconds": window_seconds,
        "analysis_hop_seconds": hop_seconds,
        "active_voice_windows": len(margins),
        "minimum_measured_voice_over_bgm_db": min(margins) if margins else None,
        "verified_minimum_duck_db": min_duck_db if margins else None,
    }


def build_audio_filter(duration: float, bgm: dict | None) -> str:
    """Build the final mix graph. Inputs are voice=1, SFX=2, and optional BGM=3."""
    duration = _finite_number(duration, "duration", minimum=0.001)
    d = f"{duration:.6f}"
    common = (
        f"[1:a]aformat=sample_rates=48000:channel_layouts=stereo,apad,atrim=duration={d}[voice_norm];"
        f"[2:a]aformat=sample_rates=48000:channel_layouts=stereo,apad,atrim=duration={d}[sfx];"
    )
    if bgm is None:
        return common + "[voice_norm][sfx]amix=inputs=2:duration=first:normalize=0[program];" + f"[program]loudnorm=I={TARGET_LUFS}:TP={TRUE_PEAK_DBTP}:LRA=7[a]"

    fade_in = min(FADE_IN_SECONDS, duration)
    fade_out = min(FADE_OUT_SECONDS, duration)
    fade_out_start = max(0.0, duration - fade_out)
    gain_db = float(bgm.get("gain_db", -22.0))
    bgm_chain = (
        "[voice_norm]asplit=2[voice_program][voice_sidechain];"
        "[voice_program][sfx]amix=inputs=2:duration=first:normalize=0[program];"
        f"[3:a]aformat=sample_rates=48000:channel_layouts=stereo,apad,atrim=duration={d},volume={gain_db:.3f}dB,"
        f"afade=t=in:st=0:d={fade_in:.6f},afade=t=out:st={fade_out_start:.6f}:d={fade_out:.6f}[bgm_norm];"
        "[bgm_norm][voice_sidechain]sidechaincompress=threshold=0.005:ratio=20:attack=20:release=250:makeup=1[bgm_ducked];"
        "[program][bgm_ducked]amix=inputs=2:duration=first:normalize=0[program_bgm];"
    )
    return common + bgm_chain + f"[program_bgm]loudnorm=I={TARGET_LUFS}:TP={TRUE_PEAK_DBTP}:LRA=7[a]"


def mix_report(bgm: dict) -> dict:
    return {
        "source_id": bgm["source_id"],
        "stem_normalization_lufs": TARGET_LUFS,
        "requested_bgm_gain_after_normalization_db": bgm.get("requested_gain_db", bgm["gain_db"]),
        "effective_bgm_gain_after_normalization_db": bgm["gain_db"],
        "minimum_duck_below_voice_db": MIN_BGM_DUCK_DB,
        "sidechain": {"threshold": 0.005, "ratio": 20, "attack_ms": 20, "release_ms": 250},
        "fade_in_seconds": FADE_IN_SECONDS,
        "fade_out_seconds": FADE_OUT_SECONDS,
        "final_target_lufs": TARGET_LUFS,
        "true_peak_limit_dbtp": TRUE_PEAK_DBTP,
        "looping": False,
        "duck_analysis": bgm.get("duck_analysis"),
    }
