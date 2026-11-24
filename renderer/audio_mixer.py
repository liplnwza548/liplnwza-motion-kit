#!/usr/bin/env python3
"""liplnwza-motion-v3.4 Audio Mixer:
- 3 Original Royalty-Free Channel BGMs (192k MP3 loops in assets_v3/bgm/):
  1) funk_brass (DEFAULT): 118 BPM Cory Wong-style choppy 16th-note funk guitar + slap bass + punchy brass horn stabs
  2) warm_groove: 108 BPM warm Rhodes + pluck groove
  3) mystery_pulse: 104 BPM investigative bass pulse + tension pluck
- Real external VO (vo_path) + optional custom BGM override (bgm_path)
- Broadband (-3 dB) + Mid-Band (300Hz-4kHz, -7 dB) VO-driven ducking
- Event-synced procedural Foley + 2-pass FFmpeg loudnorm (-14.5 LUFS, TP -2.0 dBTP target + alimiter -2.0 dB)
"""
import sys
sys.dont_write_bytecode = True

import json
import math
import subprocess
import tempfile
import wave
from pathlib import Path
import numpy as np
from scipy.signal import butter, sosfilt

SR = 48000
SKILL_ROOT = Path(__file__).resolve().parent.parent
BGM_DIR = Path("/tmp/liplnwza_v3_bgm")


def probe_duration(path: Path) -> float:
    out = subprocess.check_output([
        "ffprobe", "-v", "error", "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1", str(path)
    ], text=True).strip()
    return float(out)


def decode_to_stereo_48k(path: Path) -> np.ndarray:
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tf:
        tmp = Path(tf.name)
    try:
        subprocess.run([
            "ffmpeg", "-y", "-i", str(path),
            "-ar", str(SR), "-ac", "2", "-c:a", "pcm_s16le", str(tmp)
        ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        with wave.open(str(tmp), "rb") as wf:
            raw = wf.readframes(wf.getnframes())
        return (np.frombuffer(raw, dtype=np.int16).astype(np.float64) / 32768.0).reshape(-1, 2)
    finally:
        tmp.unlink(missing_ok=True)


def extract_envelope_visemes(vo_path: Path, fps: int = 24) -> list[str]:
    audio = decode_to_stereo_48k(vo_path)
    mono = audio.mean(axis=1)
    hop = int(SR // fps)
    n_frames = max(1, int(math.ceil(len(mono) / hop)))
    frame_rms = np.zeros(n_frames, dtype=np.float64)
    frame_cent = np.zeros(n_frames, dtype=np.float64)
    freqs = np.fft.rfftfreq(hop, d=1.0 / SR)
    for i in range(n_frames):
        seg = mono[i * hop:(i + 1) * hop]
        if len(seg) < 32:
            continue
        rms = float(np.sqrt(np.mean(seg * seg)))
        frame_rms[i] = rms
        if rms > 1e-4:
            spec = np.abs(np.fft.rfft(seg * np.hanning(len(seg)), n=hop))
            frame_cent[i] = float(np.sum(freqs * spec) / (float(np.sum(spec)) + 1e-9))

    nonzero = frame_rms[frame_rms > 0.005]
    gate = max(0.012, float(np.percentile(nonzero, 18)) * 0.65) if len(nonzero) else 0.015
    hi_rms = float(np.percentile(nonzero, 85)) if len(nonzero) else 0.12

    shapes = []
    for i in range(n_frames):
        r, c = frame_rms[i], frame_cent[i]
        if r < gate:
            shapes.append("CLOSED")
        elif r >= hi_rms * 0.80:
            shapes.append("AA" if c < 1750 else "EE")
        elif c < 950:
            shapes.append("OO")
        elif c < 1450:
            shapes.append("OH")
        elif c < 2350:
            shapes.append("AA" if (i % 3 != 0) else "EE")
        else:
            shapes.append("FV" if (i % 2 == 0) else "EE")
    return shapes


def _write_wav(path: Path, stereo: np.ndarray):
    pcm = (np.clip(stereo, -0.98, 0.98) * 32767.0).astype(np.int16)
    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(2)
        wf.setsampwidth(2)
        wf.setframerate(SR)
        wf.writeframes(pcm.tobytes())


def _save_mp3(buf: np.ndarray, out_mp3: Path):
    fade = int(SR * 0.005)
    buf[:fade] *= np.linspace(0, 1, fade)[:, None]
    buf[-fade:] *= np.linspace(1, 0, fade)[:, None]
    buf = buf / ((np.max(np.abs(buf)) + 1e-9) * 1.12)
    out_mp3.parent.mkdir(parents=True, exist_ok=True)
    tmp_wav = out_mp3.with_suffix(".tmp.wav")
    _write_wav(tmp_wav, buf)
    subprocess.run([
        "ffmpeg", "-y", "-i", str(tmp_wav), "-c:a", "libmp3lame", "-b:a", "192k", str(out_mp3)
    ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    tmp_wav.unlink(missing_ok=True)
    return out_mp3


def _add_mono(buf: np.ndarray, t0: float, sig: np.ndarray, gain: float = 1.0, pan: float = 0.0):
    i0 = int(round(t0 * SR))
    if i0 < 0 or i0 >= len(buf):
        return
    n = min(len(sig), len(buf) - i0)
    if n <= 0:
        return
    buf[i0:i0 + n, 0] += sig[:n] * (gain * math.sqrt(0.5 * (1.0 - pan)))
    buf[i0:i0 + n, 1] += sig[:n] * (gain * math.sqrt(0.5 * (1.0 + pan)))


# ===== 3 SIGNATURE ROYALTY-FREE BGM COMPOSERS =====

def compose_funk_brass_mp3(out_mp3: Path):
    """118 BPM Cory Wong-style Choppy Funk + Punchy Brass Horn Section Stabs + Slap Bass + Tight Funk Drums."""
    bpm = 118.0
    beat_s = 60.0 / bpm
    sixteenth = beat_s / 4.0
    bars = 8
    dur = bars * 4 * beat_s  # ~16.27s seamless loop
    n = int(round(dur * SR))
    buf = np.zeros((n, 2), dtype=np.float64)
    rng = np.random.default_rng(118)

    # Funky E-minor / A9 / D9 / B7#9 groove (classic Cory Wong / Vulfpeck pocket!)
    # Guitar triad voicings (upper register for crisp percussive chicken-scratch chop)
    g_chords = [
        [329.63, 392.00, 493.88, 587.33],  # Em7
        [329.63, 440.00, 493.88, 554.37],  # A9
        [329.63, 392.00, 493.88, 587.33],  # Em7
        [293.66, 369.99, 440.00, 523.25],  # D9 -> turnaround
    ]
    # Brass section voicings (Trombone + Alto Sax + Trumpet octave punch!)
    brass_hits = [
        [164.81, 329.63, 392.00, 493.88, 659.25],  # Em7 horn stab
        [185.00, 369.99, 440.00, 554.37, 659.25],  # A13 horn stab
        [196.00, 392.00, 493.88, 587.33, 783.99],  # G6/Em9 horn stab
        [246.94, 311.13, 440.00, 587.33, 739.99],  # B7#9 turnaround stab!
    ]
    bass_roots = [82.41, 110.00, 82.41, 98.00]  # E2, A2, E2, G2

    def funk_guitar_chop(freqs, accent=True):
        d = 0.085 if accent else 0.042
        t = np.linspace(0, d, int(SR * d), endpoint=False)
        sig = np.zeros_like(t)
        for f in freqs:
            # Bright saw-like harmonic bite for stratocaster bridge pickup chop
            sig += (0.55 * np.sin(2*np.pi*f*t) + 0.30 * np.sin(2*np.pi*2*f*t) + 0.15 * np.sin(2*np.pi*3*f*t))
        # Percussive pick scratch transient
        scratch = rng.standard_normal(len(t)) * np.exp(-t * 140.0) * (0.45 if accent else 0.75)
        env = np.exp(-t * (28.0 if accent else 65.0)) * (1.0 - np.exp(-t * 600.0))
        raw = (sig / len(freqs) + scratch) * env
        sos = butter(3, [750, 5200], btype="bandpass", fs=SR, output="sos")
        return sosfilt(sos, raw)

    def brass_stab(freqs, d=0.22):
        t = np.linspace(0, d, int(SR * d), endpoint=False)
        sig = np.zeros_like(t)
        # Bright brassy harmonic stack with fast brass swell & crisp cutoff
        env = (1.0 - np.exp(-t * 95.0)) * np.exp(-t * 4.8)
        # Pitch lip-scoop upward into note on attack (signature real horn feel!)
        scoop = 1.0 - 0.028 * np.exp(-t * 55.0)
        for idx_f, f in enumerate(freqs):
            phase = 2 * np.pi * np.cumsum(f * scoop) / SR
            # Rich odd+even harmonics for trumpet/sax bite
            voice = (0.50*np.sin(phase) + 0.32*np.sin(2*phase) + 0.22*np.sin(3*phase)
                     + 0.14*np.sin(4*phase) + 0.09*np.sin(5*phase))
            sig += voice * (1.0 if idx_f < 3 else 0.8)
        raw = (sig / len(freqs)) * env
        sos = butter(3, [260, 4800], btype="bandpass", fs=SR, output="sos")
        return sosfilt(sos, raw)

    def slap_bass(freq, pop=False):
        d = 0.20 if not pop else 0.13
        t = np.linspace(0, d, int(SR * d), endpoint=False)
        f_use = freq * (2.0 if pop else 1.0)
        # Thumpy fundamental + metallic slap transient
        thump = 0.75 * np.sin(2*np.pi*f_use*t) + 0.35 * np.sin(2*np.pi*2*f_use*t) + 0.18 * np.sin(2*np.pi*3*f_use*t)
        slap = rng.standard_normal(len(t)) * np.exp(-t * 180.0) * (0.45 if pop else 0.22)
        env = np.exp(-t * (14.0 if pop else 10.5)) * (1.0 - np.exp(-t * 450.0))
        sos = butter(2, 2400, btype="lowpass", fs=SR, output="sos")
        return sosfilt(sos, (thump + slap) * env)

    def funk_kick():
        d = 0.15
        t = np.linspace(0, d, int(SR * d), endpoint=False)
        f = 165.0 * np.exp(-t * 28.0) + 52.0
        click = rng.standard_normal(len(t)) * np.exp(-t * 220.0) * 0.25
        return (np.sin(2*np.pi*np.cumsum(f)/SR) + click) * np.exp(-t * 20.0) * (1.0 - np.exp(-t * 500.0))

    def funk_snare(ghost=False):
        d = 0.11 if not ghost else 0.055
        t = np.linspace(0, d, int(SR * d), endpoint=False)
        body = np.sin(2*np.pi*210*t) * np.exp(-t * 32.0) * (0.55 if not ghost else 0.25)
        wire = rng.standard_normal(len(t)) * np.exp(-t * (28.0 if not ghost else 75.0))
        sos = butter(2, 1800, btype="highpass", fs=SR, output="sos")
        return (body + sosfilt(sos, wire) * (0.65 if not ghost else 0.30))

    def funk_hat(open_h=False):
        d = 0.095 if open_h else 0.032
        t = np.linspace(0, d, int(SR * d), endpoint=False)
        ns = rng.standard_normal(len(t))
        sos = butter(3, 7200, btype="highpass", fs=SR, output="sos")
        return sosfilt(sos, ns) * np.exp(-t * (24.0 if open_h else 105.0))

    kick_s = funk_kick()
    snare_s = funk_snare(False)
    ghost_s = funk_snare(True)
    hat_c = funk_hat(False)
    hat_o = funk_hat(True)

    # 16th-note Cory Wong right-hand strum pattern (1=accent chop, 0=muted chicka)
    gtr_pat = [1, 0, 1, 0, 0, 1, 0, 1, 0, 0, 1, 0, 1, 0, 1, 0]
    for bar in range(bars):
        t_bar = bar * 4 * beat_s
        ci = bar % 4
        gc = g_chords[ci]
        bh = brass_hits[ci]
        rt = bass_roots[ci]

        # 1. Choppy 16th-note Funk Guitar (stereo panned right-center)
        for s16, hit in enumerate(gtr_pat):
            _add_mono(buf, t_bar + s16 * sixteenth, funk_guitar_chop(gc, accent=bool(hit)),
                      gain=0.22 if hit else 0.10, pan=0.28)

        # 2. Punchy Brass Horn Section Stabs (syncopated funk hits + bar-4/8 turnaround!)
        horn_steps = [(0, 0.26, 0.34), (6, 0.16, 0.28), (10, 0.20, 0.32)]
        if bar % 2 == 1:
            horn_steps.append((14, 0.18, 0.36))  # Exciting pickup stab!
        for s16, hdur, hgain in horn_steps:
            _add_mono(buf, t_bar + s16 * sixteenth, brass_stab(bh, d=hdur), gain=hgain, pan=-0.22)

        # 3. Bouncy Slap Bassline
        bass_steps = [(0, 1.0, False, 0.38), (3, 1.0, True, 0.24), (6, 1.189, False, 0.32),
                      (8, 1.335, False, 0.30), (10, 1.5, True, 0.26), (14, 1.189, False, 0.32)]
        for s16, mult, is_pop, bgain in bass_steps:
            _add_mono(buf, t_bar + s16 * sixteenth, slap_bass(rt * mult, pop=is_pop), gain=bgain, pan=0.0)

        # 4. Tight Funk Drum Pocket (Kick + Snare on 2&4 + ghost notes + 16th hats)
        for s16 in (0, 6, 10):
            _add_mono(buf, t_bar + s16 * sixteenth, kick_s, gain=0.40, pan=0.0)
        for s16 in (4, 12):
            _add_mono(buf, t_bar + s16 * sixteenth, snare_s, gain=0.34, pan=0.04)
        for s16 in (7, 9, 15):
            _add_mono(buf, t_bar + s16 * sixteenth, ghost_s, gain=0.14, pan=0.06)
        for s16 in range(16):
            is_op = (s16 == 14)
            _add_mono(buf, t_bar + s16 * sixteenth, hat_o if is_op else hat_c,
                      gain=0.13 if s16 % 2 == 0 else 0.07, pan=-0.16)

    return _save_mp3(buf, out_mp3)


def compose_warm_groove_mp3(out_mp3: Path):
    """108 BPM warm upbeat Rhodes + pluck groove (for relaxed storytelling)."""
    bpm = 108.0
    beat_s = 60.0 / bpm
    bars = 8
    dur = bars * 4 * beat_s
    n = int(round(dur * SR))
    buf = np.zeros((n, 2), dtype=np.float64)
    rng = np.random.default_rng(108)
    chords = [
        [174.61, 220.00, 261.63, 329.63], [196.00, 246.94, 293.66, 329.63],
        [164.81, 196.00, 246.94, 293.66], [220.00, 261.63, 329.63, 392.00],
    ]
    roots = [87.31, 98.00, 82.41, 110.00]
    for bar in range(bars):
        t_bar = bar * 4 * beat_s
        ch, rt = chords[bar % 4], roots[bar % 4]
        for sub, g_ch in [(0.0, 0.14), (2.5, 0.09)]:
            for ni, f in enumerate(ch):
                t = np.linspace(0, beat_s * 1.8, int(SR * beat_s * 1.8), endpoint=False)
                sig = (0.72*np.sin(2*np.pi*f*t) + 0.18*np.sin(4*np.pi*f*t)) * np.exp(-t*2.6) * (1-np.exp(-t*180))
                _add_mono(buf, t_bar + sub * beat_s, sig, gain=g_ch, pan=-0.25 + ni * 0.16)
        for sub, mult in [(0.0, 1.0), (2.5, 1.0), (3.5, 1.25)]:
            t = np.linspace(0, 0.25, int(SR * 0.25), endpoint=False)
            _add_mono(buf, t_bar + sub * beat_s, np.sin(2*np.pi*rt*mult*t) * np.exp(-t*9.0), gain=0.28, pan=0.0)
        for h_i in range(8):
            t = np.linspace(0, 0.035, int(SR * 0.035), endpoint=False)
            sos = butter(3, 6500, btype="highpass", fs=SR, output="sos")
            hat = sosfilt(sos, rng.standard_normal(len(t))) * np.exp(-t * 85.0)
            _add_mono(buf, t_bar + h_i * 0.5 * beat_s, hat, gain=0.09 if h_i % 2 == 0 else 0.05, pan=0.1)
    return _save_mp3(buf, out_mp3)


def compose_mystery_pulse_mp3(out_mp3: Path):
    """104 BPM deep investigative bass pulse + muted tension ticks (for serious/warning clips)."""
    bpm = 104.0
    beat_s = 60.0 / bpm
    bars = 8
    dur = bars * 4 * beat_s
    n = int(round(dur * SR))
    buf = np.zeros((n, 2), dtype=np.float64)
    roots = [73.42, 73.42, 65.41, 69.30]  # Dm -> C -> C#/A tension
    arps = [[293.66, 349.23, 440.00], [293.66, 349.23, 523.25], [261.63, 329.63, 392.00], [277.18, 329.63, 440.00]]
    for bar in range(bars):
        t_bar = bar * 4 * beat_s
        rt, ap = roots[bar % 4], arps[bar % 4]
        for s8 in range(8):
            t = np.linspace(0, 0.22, int(SR * 0.22), endpoint=False)
            pulse = (0.8*np.sin(2*np.pi*rt*t) + 0.25*np.sin(4*np.pi*rt*t)) * np.exp(-t * 11.0)
            _add_mono(buf, t_bar + s8 * 0.5 * beat_s, pulse, gain=0.28 if s8 % 2 == 0 else 0.16, pan=0.0)
            f_a = ap[s8 % 3]
            pluck = np.sin(2*np.pi*f_a*t) * np.exp(-t * 18.0)
            _add_mono(buf, t_bar + s8 * 0.5 * beat_s, pluck, gain=0.12, pan=-0.22 if s8 % 2 == 0 else 0.22)
    return _save_mp3(buf, out_mp3)


def ensure_bgm_library():
    tracks = {
        "funk_brass": compose_funk_brass_mp3,
        "warm_groove": compose_warm_groove_mp3,
        "mystery_pulse": compose_mystery_pulse_mp3,
    }
    for name, fn in tracks.items():
        p = BGM_DIR / f"{name}.mp3"
        if not p.exists():
            fn(p)


def synth_pop(pitch=520.0):
    t = np.linspace(0, 0.095, int(SR * 0.095), endpoint=False)
    return np.sin(2 * np.pi * (pitch * np.exp(t * 7.5)) * t) * np.exp(-t * 36.0) * (1.0 - np.exp(-t * 320.0))


def synth_tick():
    t = np.linspace(0, 0.06, int(SR * 0.06), endpoint=False)
    return (0.65 * np.sin(2 * np.pi * 1550 * t) + 0.35 * np.sin(2 * np.pi * 2450 * t)) * np.exp(-t * 65.0)


def synth_whoosh():
    n = int(SR * 0.18)
    noise = np.random.default_rng(42).standard_normal(n)
    sos = butter(3, [350, 3400], btype="bandpass", fs=SR, output="sos")
    return sosfilt(sos, noise) * (np.sin(np.pi * np.linspace(0, 1, n)) ** 1.5) * 0.45


def synth_chime():
    t = np.linspace(0, 0.30, int(SR * 0.30), endpoint=False)
    return (0.6 * np.sin(2 * np.pi * 880 * t) + 0.4 * np.sin(2 * np.pi * 1318.5 * t)) * np.exp(-t * 9.5)


def apply_vo_midband_ducking(bgm: np.ndarray, vo: np.ndarray) -> np.ndarray:
    n = len(bgm)
    vo_mono = vo[:n].mean(axis=1)
    if len(vo_mono) < n:
        vo_mono = np.pad(vo_mono, (0, n - len(vo_mono)))
    win = int(SR * 0.05)
    env = np.sqrt(np.convolve(vo_mono * vo_mono, np.ones(win) / win, mode="same"))
    active = np.clip((env - 0.012) / 0.035, 0.0, 1.0)
    sos_mid = butter(3, [300, 4000], btype="bandpass", fs=SR, output="sos")
    bgm_mid = np.column_stack([sosfilt(sos_mid, bgm[:, 0]), sosfilt(sos_mid, bgm[:, 1])])
    bgm_rest = bgm - bgm_mid
    return bgm_rest * (1.0 - active * (1.0 - 0.708))[:, None] + bgm_mid * (1.0 - active * (1.0 - 0.316))[:, None]


def build_audio_track(spec: dict, duration: float, out_wav: Path):
    ensure_bgm_library()
    n = int(math.ceil(duration * SR))
    audio_cfg = spec.get("audio") or {}
    vo_path = Path(audio_cfg["vo_path"]) if audio_cfg.get("vo_path") else None

    if audio_cfg.get("bgm_path"):
        bgm_path = Path(audio_cfg["bgm_path"])
    else:
        preset = str(audio_cfg.get("bgm_preset", "funk_brass"))
        bgm_path = BGM_DIR / f"{preset}.mp3"
        if not bgm_path.exists():
            bgm_path = BGM_DIR / "funk_brass.mp3"

    has_vo = bool(vo_path and vo_path.exists())
    bgm_raw = decode_to_stereo_48k(bgm_path)
    reps = int(math.ceil(n / max(1, len(bgm_raw))))
    bgm_gain = float(audio_cfg.get("bgm_gain", 0.22 if has_vo else 0.58))
    bgm = np.tile(bgm_raw, (reps, 1))[:n] * bgm_gain

    vo = np.zeros((n, 2), dtype=np.float64)
    if has_vo:
        vo_raw = decode_to_stereo_48k(vo_path)
        vo_norm = vo_raw * (0.82 / (float(np.max(np.abs(vo_raw))) + 1e-9))
        m = min(n, len(vo_norm))
        vo[:m] = vo_norm[:m]
        bgm = apply_vo_midband_ducking(bgm, vo)

    foley = np.zeros((n, 2), dtype=np.float64)
    whoosh, pop_hi, pop_lo, tick, chime = synth_whoosh(), synth_pop(540.0), synth_pop(420.0), synth_tick(), synth_chime()
    f_scale = 0.62 if has_vo else 1.0

    for idx, beat in enumerate(spec.get("beats", [])):
        t_b = float(beat.get("start", 0.0))
        if idx > 0:
            _add_mono(foley, t_b, whoosh, gain=0.35 * f_scale, pan=0.0)
        _add_mono(foley, t_b + 0.04, pop_hi, gain=0.24 * f_scale, pan=0.12)
        wtype = (beat.get("widget") or {}).get("type", "")
        if wtype in ("checklist_ticks", "score_grid", "rating_stars"):
            for s in range(3):
                _add_mono(foley, t_b + 0.26 + s * 0.22, tick, gain=0.19 * f_scale, pan=0.15)
        elif wtype in ("cta_comment_box", "media_clip_frame"):
            _add_mono(foley, t_b + 0.30, chime, gain=0.22 * f_scale, pan=0.0)

    for row in spec.get("word_rows", []):
        for wi, w in enumerate(row.get("words", [])):
            _add_mono(foley, float(w["start"]), pop_lo, gain=0.10 * f_scale, pan=-0.12 if wi % 2 == 0 else 0.12)

    mix = vo + bgm + foley
    raw_wav = out_wav.with_name(out_wav.stem + "_raw.wav")
    _write_wav(raw_wav, mix)

    res = subprocess.run([
        "ffmpeg", "-y", "-i", str(raw_wav),
        "-af", "loudnorm=I=-14.5:TP=-2.0:LRA=11:print_format=json", "-f", "null", "-"
    ], stderr=subprocess.PIPE, text=True, check=True)
    m = json.loads(res.stderr[res.stderr.rfind("{"):res.stderr.rfind("}") + 1])
    af = (
        f"loudnorm=I=-14.5:TP=-2.0:LRA=11:linear=true:"
        f"measured_I={m['input_i']}:measured_TP={m['input_tp']}:"
        f"measured_LRA={m['input_lra']}:measured_thresh={m['input_thresh']}:"
        f"offset={m['target_offset']},alimiter=limit=-2.0dB:level=false:attack=5:release=50"
    )
    subprocess.run([
        "ffmpeg", "-y", "-i", str(raw_wav), "-af", af,
        "-ar", str(SR), "-ac", "2", str(out_wav)
    ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    raw_wav.unlink(missing_ok=True)
    return out_wav
