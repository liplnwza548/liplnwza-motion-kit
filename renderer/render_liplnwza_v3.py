#!/usr/bin/env python3
"""liplnwza-motion-v3.4 Lean & Fast Offline Headless Chromium CDP Renderer.
- 24fps standard + JPEG q=92 CDP capture (~2x faster than PNG!)
- Ultra-lean transparent WebP assets (16 full-body poses + 12 props) with Lazy Asset Injection
- Calm grounded mascot OUTSIDE camera-rig (zero jitter; camera/transitions animate only widget stage + bg)
- 3 Original Royalty-Free BGMs (funk_brass default, warm_groove, mystery_pulse)
- Dual-Mode Lip-Sync (visemes.json OR 24fps real audio-envelope) + --chunk-frames
"""
import sys
sys.dont_write_bytecode = True

import argparse
import base64
import io
import json
import math
import shutil
import subprocess
import tempfile
import time
from pathlib import Path

from PIL import Image, ImageDraw
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

SCRIPT_DIR = Path(__file__).resolve().parent
SKILL_ROOT = SCRIPT_DIR.parent
sys.path.insert(0, str(SCRIPT_DIR))
import audio_mixer

W, H = 720, 1280
FPS = 24


def find_system_fonts_css() -> str:
    """Embed system NotoSansThai (or bundled Prompt-Bold fallback on Windows) directly into HTML."""
    bold_candidates = [
        Path("/usr/share/fonts/truetype/noto/NotoSansThai-Bold.ttf"),
        SKILL_ROOT / "assets" / "fonts" / "Prompt-Bold.ttf",
        Path(r"C:\Windows\Fonts\NotoSansThai-Bold.ttf"),
    ]
    reg_candidates = [
        Path("/usr/share/fonts/truetype/noto/NotoSansThai-Regular.ttf"),
        SKILL_ROOT / "assets" / "fonts" / "Prompt-Bold.ttf",
        Path(r"C:\Windows\Fonts\NotoSansThai-Regular.ttf"),
    ]
    noto_bold = next((p for p in bold_candidates if p.exists()), None)
    noto_reg  = next((p for p in reg_candidates if p.exists()), None)
    css = []
    if noto_bold:
        b64 = base64.b64encode(noto_bold.read_bytes()).decode("ascii")
        css.append(f"@font-face {{ font-family: 'NotoThai'; src: url(data:font/ttf;base64,{b64}) format('truetype'); font-weight: 700 900; }}")
    if noto_reg:
        b64 = base64.b64encode(noto_reg.read_bytes()).decode("ascii")
        css.append(f"@font-face {{ font-family: 'NotoThai'; src: url(data:font/ttf;base64,{b64}) format('truetype'); font-weight: 400; }}")
    return "\n".join(css)


def load_lazy_v3_assets(assets_dir: Path, spec: dict) -> dict:
    """Lazy Asset Injection: load ONLY the WebP/PNG poses & props referenced in spec."""
    mascot_dir = assets_dir / "mascot"
    props_dir = assets_dir / "props"
    anchors = json.loads((mascot_dir / "mouth_anchors.json").read_text(encoding="utf-8"))

    used_poses = {b.get("pose", "wave") for b in spec.get("beats", [])} | {"wave"}
    used_props = {b.get("sidekick", "") for b in spec.get("beats", []) if b.get("sidekick")}

    def encode_img(folder: Path, stem: str):
        for ext, mime in ((".webp", "image/webp"), (".png", "image/png")):
            p = folder / f"{stem}{ext}"
            if p.exists():
                return f"data:{mime};base64," + base64.b64encode(p.read_bytes()).decode("ascii")
        return None

    mascots = {}
    for k in sorted(used_poses):
        uri = encode_img(mascot_dir, k)
        if uri:
            mascots[k] = uri

    props = {}
    for k in sorted(used_props):
        uri = encode_img(props_dir, k)
        if uri:
            props[k] = uri

    return {"mascots": mascots, "anchors": {k: anchors[k] for k in mascots if k in anchors}, "props": props}


def load_dedup_visemes(visemes_path: Path) -> list[tuple[float, str]]:
    raw = json.loads(visemes_path.read_text(encoding="utf-8"))
    items = raw["visemes"] if isinstance(raw, dict) and "visemes" in raw else raw
    by_t = {}
    for it in items:
        by_t[round(float(it["start"]), 4)] = str(it["shape"]).upper()
    return sorted(by_t.items(), key=lambda x: x[0])


def build_viseme_timeline(spec: dict, total_frames: int, fps: int = FPS) -> tuple[list[str], str]:
    audio_cfg = spec.get("audio") or {}
    vpath = Path(audio_cfg["visemes_path"]) if audio_cfg.get("visemes_path") else None
    vo_path = Path(audio_cfg["vo_path"]) if audio_cfg.get("vo_path") else None

    if vpath and vpath.exists():
        cues = load_dedup_visemes(vpath)
        timeline, ci, cur = [], 0, "CLOSED"
        for f in range(total_frames):
            t = f / fps
            while ci < len(cues) and cues[ci][0] <= t + 1e-4:
                cur = cues[ci][1]
                ci += 1
            timeline.append(cur)
        return timeline, f"studio_visemes ({len(cues)} cues)"

    if vo_path and vo_path.exists():
        shapes = audio_mixer.extract_envelope_visemes(vo_path, fps)
        if len(shapes) < total_frames:
            shapes.extend(["CLOSED"] * (total_frames - len(shapes)))
        return shapes[:total_frames], "express_audio_envelope"

    rows = spec.get("word_rows", [])
    cycle = ("AA", "EE", "OH", "OO", "FV", "AA")
    return [cycle[int((f / fps) * 8.5) % len(cycle)] if any(r["start"] <= f / fps <= r["end"] for r in rows) else "CLOSED"
            for f in range(total_frames)], "demo_word_rows"


def extract_lemo_clip_frames(clip_path: Path, target_fps: int = 24, tw: int = 518, th: int = 310) -> list[str]:
    """Auto-normalize ANY Lemo-Opuscar clip (9:16 or 16:9, any fps) into crisp JPEG frames (518x310 TV or 720x1280 full-bleed)."""
    if not clip_path.exists():
        return []
    tmpdir = Path(tempfile.mkdtemp(prefix="lemo_tv_"))
    try:
        subprocess.run([
            "ffmpeg", "-y", "-i", str(clip_path),
            "-vf", f"fps={target_fps},scale={tw}:{th}:force_original_aspect_ratio=increase,crop={tw}:{th}",
            "-q:v", "4", str(tmpdir / "f_%05d.jpg")
        ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return ["data:image/jpeg;base64," + base64.b64encode(fp.read_bytes()).decode("ascii")
                for fp in sorted(tmpdir.glob("f_*.jpg"))]
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)


def launch_browser():
    opts = Options()
    for cand in (
        "/usr/bin/chromium",
        "/usr/bin/google-chrome",
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    ):
        if Path(cand).exists():
            opts.binary_location = cand
            break
    opts.add_argument("--headless=new")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--disable-gpu-sandbox")
    opts.add_argument("--enable-webgl")
    opts.add_argument("--ignore-gpu-blocklist")
    opts.add_argument("--use-gl=angle")
    opts.add_argument("--use-angle=swiftshader")
    opts.add_argument("--enable-unsafe-swiftshader")
    opts.add_argument(f"--window-size={W},{H}")
    driver = webdriver.Chrome(options=opts)
    driver.execute_cdp_cmd("Emulation.setDeviceMetricsOverride", {
        "width": W, "height": H, "deviceScaleFactor": 1, "mobile": False
    })
    return driver


def prepare_page(driver, spec: dict, assets_bundle: dict):
    tpl = (SCRIPT_DIR / "stage_template.html").read_text(encoding="utf-8")
    wjs = (SCRIPT_DIR / "widgets.js").read_text(encoding="utf-8")
    fonts_css = find_system_fonts_css()
    html = (
        tpl.replace("/* FONT_INJECT_PLACEHOLDER */", fonts_css)
           .replace("/* ASSETS_INJECT_PLACEHOLDER */", f"window.__ASSETS__ = {json.dumps(assets_bundle)};")
           .replace("/* SPEC_INJECT_PLACEHOLDER */", f"window.__SPEC__ = {json.dumps(spec, ensure_ascii=False)};")
           .replace("/* WIDGETS_JS_PLACEHOLDER */", wjs)
    )
    driver.get("about:blank")
    driver.execute_script("document.open(); document.write(arguments[0]); document.close();", html)
    driver.execute_script("return document.fonts.ready;")


def capture_frame_jpg(driver) -> bytes:
    """Fast JPEG q=92 CDP capture (~2x faster than PNG with broadcast-sharp quality)."""
    res = driver.execute_cdp_cmd("Page.captureScreenshot", {"format": "jpeg", "quality": 92})
    return base64.b64decode(res["data"])


def render_qa_sheet(driver, spec: dict, viseme_timeline: list[str], lemo_clips: dict, out_jpg: Path, fps: int = FPS):
    beats = spec.get("beats", [])
    shots = []
    for b in beats:
        t = float(b["qa_at"]) if b.get("qa_at") is not None else (b["start"] + (b["end"] - b["start"]) * 0.72)
        fidx = min(len(viseme_timeline) - 1, max(0, int(round(t * fps))))
        pose = b.get("pose", "wave")
        m_shape = viseme_timeline[fidx]
        sk = b.get("sidekick", "")
        tv_uri = ""
        w = b.get("widget") or {}
        if w.get("type") == "media_clip_frame" and w.get("clip_path") in lemo_clips:
            frames = lemo_clips[w["clip_path"]]
            if frames:
                tv_uri = frames[int((t - b["start"]) * fps) % len(frames)]
        driver.execute_script("window.renderAtTime(arguments[0], arguments[1], arguments[2], arguments[3], arguments[4]);",
                              t, pose, m_shape, sk, tv_uri)
        jpg = capture_frame_jpg(driver)
        shot_tag = b.get("mascot_shot") or w.get("type", "")
        shots.append((b["id"], pose, m_shape, shot_tag, Image.open(io.BytesIO(jpg)).convert("RGB")))

    cols = 4 if len(shots) >= 8 else max(2, len(shots))
    rows = math.ceil(len(shots) / cols)
    cw, ch, pad = 360, 640, 16
    sheet = Image.new("RGB", (cols * (cw + pad) + pad, rows * (ch + pad) + pad), (24, 27, 38))
    draw = ImageDraw.Draw(sheet)
    for i, (bid, pose, m_shape, wtype, im) in enumerate(shots):
        r, c = divmod(i, cols)
        x, y = pad + c * (cw + pad), pad + r * (ch + pad)
        sheet.paste(im.resize((cw, ch), Image.Resampling.LANCZOS), (x, y))
        draw.rectangle([x, y, x + cw, y + 30], fill=(24, 27, 38))
        draw.text((x + 10, y + 7), f"{bid} | {pose} ({m_shape}) | {wtype}", fill=(255, 214, 72))
    out_jpg.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(out_jpg, quality=92)
    print(f"QA_SHEET: {out_jpg} ({len(shots)} shots, {cols}x{rows})")


def render_mp4(driver, spec: dict, duration: float, viseme_timeline: list[str], lemo_clips: dict, out_mp4: Path, chunk_frames: int = 120, fps: int = FPS):
    t0_wall = time.time()
    total_frames = int(round(duration * fps))
    tmpdir = Path(tempfile.mkdtemp(prefix="liplnwza_v36_"))
    try:
        audio_wav = tmpdir / "master_audio.wav"
        audio_mixer.build_audio_track(spec, duration, audio_wav)

        beats = spec.get("beats", [])
        chunk_paths = []
        for start_f in range(0, total_frames, chunk_frames):
            end_f = min(total_frames, start_f + chunk_frames)
            cpath = tmpdir / f"chunk_{start_f:05d}.mp4"
            proc = subprocess.Popen([
                "ffmpeg", "-y",
                "-f", "image2pipe", "-vcodec", "mjpeg", "-r", str(fps), "-i", "-",
                "-vf", "scale=in_range=pc:out_range=tv,format=yuv420p",
                "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p",
                "-color_range", "tv", "-colorspace", "bt709", "-color_primaries", "bt709", "-color_trc", "bt709",
                str(cpath)
            ], stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

            for fidx in range(start_f, end_f):
                t = fidx / fps
                beat = next((b for b in beats if b["start"] <= t < b["end"]), beats[-1])
                pose = beat.get("pose", "wave")
                m_shape = viseme_timeline[fidx]
                sk = beat.get("sidekick", "")
                tv_uri = ""
                w = beat.get("widget") or {}
                if w.get("type") == "media_clip_frame" and w.get("clip_path") in lemo_clips:
                    frames = lemo_clips[w["clip_path"]]
                    if frames:
                        tv_uri = frames[int((t - beat["start"]) * fps) % len(frames)]
                driver.execute_script(
                    "window.renderAtTime(arguments[0], arguments[1], arguments[2], arguments[3], arguments[4]);",
                    t, pose, m_shape, sk, tv_uri
                )
                proc.stdin.write(capture_frame_jpg(driver))

            proc.stdin.close()
            proc.wait()
            if proc.returncode != 0:
                raise RuntimeError(f"chunk {start_f} encode failed: {proc.returncode}")
            chunk_paths.append(cpath)

        concat_txt = tmpdir / "chunks.txt"
        concat_txt.write_text("\n".join(f"file '{p}'" for p in chunk_paths), encoding="utf-8")
        raw_mp4 = tmpdir / "video_only.mp4"
        subprocess.run([
            "ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(concat_txt),
            "-c", "copy", str(raw_mp4)
        ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        out_mp4.parent.mkdir(parents=True, exist_ok=True)
        final_tmp = tmpdir / "final.mp4"
        subprocess.run([
            "ffmpeg", "-y", "-i", str(raw_mp4), "-i", str(audio_wav),
            "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
            "-shortest", "-movflags", "+faststart", str(final_tmp)
        ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        shutil.copy2(final_tmp, out_mp4)
        elapsed = time.time() - t0_wall
        print(f"RENDER_DONE: {out_mp4} ({total_frames} frames @ {fps}fps in {elapsed:.1f}s = {total_frames/elapsed:.1f} fps, {len(chunk_paths)} chunks)")
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--spec", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--assets-v3", default=str(SKILL_ROOT / "assets_v3"))
    ap.add_argument("--qa-only", action="store_true")
    ap.add_argument("--chunk-frames", type=int, default=120)
    ap.add_argument("--fps", type=int, default=None, help="Override render FPS (default: spec.fps or 24)")
    args = ap.parse_args()

    spec = json.loads(Path(args.spec).read_text(encoding="utf-8"))
    fps = int(args.fps) if args.fps else int(spec.get("fps", FPS))
    audio_cfg = spec.get("audio") or {}
    vo_path = Path(audio_cfg["vo_path"]) if audio_cfg.get("vo_path") else None
    duration = audio_mixer.probe_duration(vo_path) if (vo_path and vo_path.exists()) else float(spec.get("duration", 12.0))

    total_frames = int(round(duration * fps))
    viseme_timeline, lip_mode = build_viseme_timeline(spec, total_frames, fps=fps)
    assets_bundle = load_lazy_v3_assets(Path(args.assets_v3), spec)
    print(f"DURATION: {duration:.2f}s ({total_frames}f @ {fps}fps) | LIP: {lip_mode} | LAZY ASSETS: {len(assets_bundle['mascots'])} poses, {len(assets_bundle['props'])} props")

    lemo_clips = {}
    for b in spec.get("beats", []):
        w = b.get("widget") or {}
        if w.get("type") == "media_clip_frame" and w.get("clip_path"):
            cp = w["clip_path"]
            is_fb = (w.get("fit") == "full_bleed") or (b.get("layout") == "full_stage")
            tw, th = (W, H) if is_fb else (518, 310)
            if cp not in lemo_clips:
                lemo_clips[cp] = extract_lemo_clip_frames(Path(cp), fps, tw=tw, th=th)

    driver = launch_browser()
    try:
        prepare_page(driver, spec, assets_bundle)
        if args.qa_only:
            render_qa_sheet(driver, spec, viseme_timeline, lemo_clips, Path(args.out), fps=fps)
        else:
            render_mp4(driver, spec, duration, viseme_timeline, lemo_clips, Path(args.out), args.chunk_frames, fps=fps)
    finally:
        driver.quit()


if __name__ == "__main__":
    main()
