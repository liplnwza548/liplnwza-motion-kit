"""Locked v3.4 production-spec constants for LiplnwZa Motion Kit.

This module records the v3.4 standard (locked 2026-11-24 by Philip) as
machine-readable constants so documentation, tooling and the future v3.4
engine all read the same numbers. It is NOT a renderer: importing it
renders nothing and it must never be presented as the v3.4 engine.

Source: Notion page "LiplnwZa Motion Kit v3.4 — Production Spec, Installed
Skill & GitHub Sync Plan" (recorded via Gemini Task Web) + Philip's
direction of 2026-11-24. Canonical human-readable spec: SKILL.md at the
repo root.

Engine status: the v3.4 engine scripts and WebP assets are installed as
the `liplnwza-motion` skill on Gemini Task Web only and have NOT been
imported into this repo yet. See V34-IMPORT-CHECKLIST.md at the repo root
for the import list. ENGINE_STATUS stays "import_pending" until every
file in REQUIRED_ENGINE_FILES exists in this repo and passes its checks.
"""

ENGINE_STATUS = "import_pending"
SPEC_VERSION = "3.4"
SPEC_NAME = "Lean & Punchy"

# Output / render
WIDTH = 720
HEIGHT = 1280
FPS = 24
VIDEO_CODEC = "h264"
FASTSTART = True
CHUNK_FRAMES = 120
RENDER_ENGINE = "headless_chromium_cdp"
CAPTURE_JPEG_QUALITY = 92
LAZY_ASSET_LOADING = True
RENDER_FONT = "NotoSansThai-Bold.ttf"

# Layout (pixels, 720x1280 canvas)
RIBBON_Y = 144
STAGE_Y_MIN = 214
STAGE_Y_MAX = 659
SUBTITLE_Y = 672
SUBTITLE_CENTERED = True
SUBTITLE_AUTOFIT = True
SUBTITLE_CLEARS_TIKTOK_UI = True
MASCOT_SIZE_PX = 500
MASCOT_BREATHING_PX = 2.2
MASCOT_STATIC_OUTSIDE_CAMERA_RIG = True

# Cameras and transitions (stage + background only; never mascot/subtitles)
CAMERAS = ("push_in", "pull_out", "focus_tv", "punch_in")
TRANSITIONS = ("paper_slide", "page_peel", "whip_zoom", "ink_flash")

# Mascot: 16 full-body mouthless clean plates (WebP, 220.8 KB total)
POSES = (
    "wave",
    "pointer",
    "clipboard",
    "confident",
    "magnify",
    "laptop_focus",
    "laptop_smile",
    "cheer",
    "facepalm",
    "thinking_chin",
    "shocked",
    "holding_card",
    "thumbs_up_full",
    "newspaper_hold",
    "shrug",
    "idea_finger",
)
CLEAN_PLATE_TOTAL_KB = 220.8

# Mouth: 6 vector SVG shapes driven by visemes
MOUTH_SHAPES = ("CLOSED", "AA", "EE", "OH", "OO", "FV")

# Props / supporting bots: 12 transparent WebP (88.4 KB total)
PROPS = (
    "bot_curious",
    "bot_cheer",
    "bot_shock",
    "badge_alert",
    "badge_check",
    "badge_question",
    "pointer_stick",
    "clipboard",
    "magnifying_glass",
    "laptop",
    "newspaper",
    "lightbulb",
)
PROPS_TOTAL_KB = 88.4

# Lemo TV slot
TV_SLOT_NAME = "media_clip_frame"
TV_CLIP_MIN_SECONDS = 4
TV_CLIP_MAX_SECONDS = 6
TV_CLIP_SOURCE = "Lemo-Opuscar"
TV_CLIP_STYLE_COUNT = 25

# Lip-sync modes
LIP_SYNC_MODES = ("studio", "express")
LIP_SYNC_STUDIO_SOURCE = "visemes.json (MFA)"
LIP_SYNC_EXPRESS_FPS = 24
LIP_SYNC_EXPRESS_SOURCE = "vo_path waveform"

# Audio: self-licensed BGM generated under /tmp/liplnwza_v3_bgm/
BGM_DIR = "/tmp/liplnwza_v3_bgm/"
BGM_STYLES = {
    "funk_brass": 118,   # main track: Cory Wong Funk + Brass Stabs
    "warm_groove": 108,
    "mystery_pulse": 104,
}
BGM_MAIN_STYLE = "funk_brass"
DUCKING_BAND_HZ = (300, 4000)
LOUDNESS_LUFS = -14.5
LOUDNESS_PASSES = 2
TRUE_PEAK_MAX_DBTP = -1.0

# Files that must exist in this repo before ENGINE_STATUS may change.
# Target paths are PROPOSED (to confirm against the Gemini export on
# import); the filenames are the locked part. Do not invent these files:
# they arrive with the export from the installed Gemini skill.
REQUIRED_ENGINE_FILES = (
    "renderer/render_liplnwza_v3.py",
    "renderer/audio_mixer.py",
    "renderer/stage_template.html",
    "renderer/widgets.js",
    "renderer/mouth_anchors.json",
    "assets/mascot/v34/clean_plates/",  # 16 WebP poses
    "assets/mascot/v34/props/",         # 12 WebP props
    "assets/mascot/v34/mouths/",        # 6 SVG mouth shapes
)
