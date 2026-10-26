"""Load immutable, version-pinned theme configuration for the renderer."""
from __future__ import annotations

import copy
import hashlib
import json
import re
from pathlib import Path

from theme_assets import resolve_asset


_ID = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
_VERSION = re.compile(r"^v[0-9]{3}$")
_COLOR = re.compile(r"^#[0-9A-Fa-f]{6}$")
_FONT_PATHS = {("prompt-bold", "v001"): Path("assets/fonts/Prompt-Bold.ttf")}
_TOP_LEVEL_KEYS = {
    "schema_version", "id", "version", "layout_profile", "font", "palette",
    "text_colors", "background", "cards", "captions", "layout", "motion", "audio",
    "background_variants", "decorations", "mascot_concept",
}
_OPTIONAL_TOP_LEVEL_KEYS = {"background_variants", "decorations", "mascot_concept"}


def _read_json(path: Path) -> dict:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"Invalid theme JSON: {path}") from exc
    if not isinstance(value, dict):
        raise ValueError(f"Theme JSON must be an object: {path}")
    return value


def _color(value, field: str) -> str:
    if not isinstance(value, str) or not _COLOR.fullmatch(value):
        raise ValueError(f"{field} must be a #RRGGBB color")
    return value.upper()


def _integer(value, field: str, low: int, high: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or not low <= value <= high:
        raise ValueError(f"{field} must be an integer in {low}..{high}")
    return value


def _number(value, field: str, low: float, high: float) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not low <= value <= high:
        raise ValueError(f"{field} must be a number in {low}..{high}")
    return float(value)


def _pair(value, field: str, low: int, high: int) -> list[int]:
    if not isinstance(value, list) or len(value) != 2:
        raise ValueError(f"{field} must contain two integers")
    return [_integer(value[0], f"{field}[0]", low, high), _integer(value[1], f"{field}[1]", low, high)]


def _asset_ref(value, field: str) -> dict:
    if not isinstance(value, dict) or set(value) != {"id", "version"}:
        raise ValueError(f"{field} must pin an asset id and version")
    if not isinstance(value["id"], str) or not _ID.fullmatch(value["id"]):
        raise ValueError(f"{field}.id is invalid")
    if not isinstance(value["version"], str) or not _VERSION.fullmatch(value["version"]):
        raise ValueError(f"{field}.version is invalid")
    return value


def _validate(config: dict, theme_id: str, version: str) -> dict:
    unknown = set(config) - _TOP_LEVEL_KEYS
    missing = (_TOP_LEVEL_KEYS - _OPTIONAL_TOP_LEVEL_KEYS) - set(config)
    if unknown:
        raise ValueError(f"Unsupported theme fields: {', '.join(sorted(unknown))}")
    if missing:
        raise ValueError(f"Missing theme fields: {', '.join(sorted(missing))}")
    if config.get("schema_version") != 1:
        raise ValueError("Unsupported theme schema_version")
    if (config.get("id"), config.get("version")) != (theme_id, version):
        raise ValueError("Theme file identity does not match its pinned path")
    if config.get("layout_profile") != "paper-v021":
        raise ValueError("Only the paper-v021 layout profile is supported in phase 1")

    font = config.get("font")
    if not isinstance(font, dict) or set(font) != {"id", "version"}:
        raise ValueError("font must pin an id and version")
    if (font.get("id"), font.get("version")) not in _FONT_PATHS:
        raise ValueError("Theme font is not an installed, pinned kit font")

    palette = config.get("palette")
    if not isinstance(palette, dict) or set(palette) != {"ink", "paper", "accents"}:
        raise ValueError("palette must contain ink, paper, and accents")
    palette["ink"] = _color(palette["ink"], "palette.ink")
    palette["paper"] = _color(palette["paper"], "palette.paper")
    if not isinstance(palette["accents"], list) or len(palette["accents"]) != 4:
        raise ValueError("palette.accents must contain four colors")
    palette["accents"] = [_color(v, f"palette.accents[{i}]") for i, v in enumerate(palette["accents"])]

    text_colors = config.get("text_colors")
    if not isinstance(text_colors, dict) or set(text_colors) != {"paper", "accents"}:
        raise ValueError("text_colors must define paper and accents")
    text_colors["paper"] = _color(text_colors["paper"], "text_colors.paper")
    if not isinstance(text_colors["accents"], list) or len(text_colors["accents"]) != 4:
        raise ValueError("text_colors.accents must contain four colors")
    text_colors["accents"] = [_color(v, f"text_colors.accents[{i}]") for i, v in enumerate(text_colors["accents"])]

    background = config.get("background")
    if not isinstance(background, dict) or set(background) != {"mode", "colors", "asset", "grid"}:
        raise ValueError("background must define mode, colors, asset, and grid")
    if background["mode"] not in {"grid", "image"}:
        raise ValueError("background.mode must be grid or image")
    if not isinstance(background["colors"], list) or not 1 <= len(background["colors"]) <= 8:
        raise ValueError("background.colors must contain 1..8 colors")
    background["colors"] = [_color(v, f"background.colors[{i}]") for i, v in enumerate(background["colors"])]
    if background["mode"] == "grid":
        if background["asset"] is not None:
            raise ValueError("grid backgrounds cannot select an image asset")
    else:
        background["asset"] = _asset_ref(background["asset"], "background.asset")
    grid = background["grid"]
    if not isinstance(grid, dict) or set(grid) != {"enabled", "step_px", "color", "opacity", "width_px"}:
        raise ValueError("background.grid is invalid")
    if not isinstance(grid["enabled"], bool):
        raise ValueError("background.grid.enabled must be boolean")
    grid["step_px"] = _integer(grid["step_px"], "background.grid.step_px", 8, 512)
    grid["color"] = _color(grid["color"], "background.grid.color")
    grid["opacity"] = _number(grid["opacity"], "background.grid.opacity", 0, 1)
    grid["width_px"] = _integer(grid["width_px"], "background.grid.width_px", 1, 12)

    variants = config.get("background_variants")
    if variants is not None:
        if not isinstance(variants, list) or not 2 <= len(variants) <= 8:
            raise ValueError("background_variants must pin 2..8 background assets")
        variant_ids = set()
        for index, variant in enumerate(variants):
            field = f"background_variants[{index}]"
            if not isinstance(variant, dict) or set(variant) != {"id", "asset", "intended_use"}:
                raise ValueError(f"{field} is invalid")
            if not isinstance(variant["id"], str) or not _ID.fullmatch(variant["id"]):
                raise ValueError(f"{field}.id is invalid")
            if variant["id"] in variant_ids:
                raise ValueError("background variant ids must be unique")
            variant_ids.add(variant["id"])
            variant["asset"] = _asset_ref(variant["asset"], f"{field}.asset")
            if not isinstance(variant["intended_use"], str) or not variant["intended_use"]:
                raise ValueError(f"{field}.intended_use must be non-empty")
        if background["mode"] != "image" or not any(
            variant["asset"] == background["asset"] for variant in variants
        ):
            raise ValueError("background.asset must match one pinned background variant")

    cards = config.get("cards")
    if not isinstance(cards, dict) or set(cards) != {"style", "border_px", "outline_px", "shadow_offset_px", "roughness_px", "padding_px"}:
        raise ValueError("cards fields do not match the phase 1 card contract")
    if cards["style"] != "rough-paper":
        raise ValueError("Only rough-paper cards are supported in phase 1")
    cards["border_px"] = _integer(cards["border_px"], "cards.border_px", 1, 24)
    cards["outline_px"] = _integer(cards["outline_px"], "cards.outline_px", 1, 32)
    cards["shadow_offset_px"] = _pair(cards["shadow_offset_px"], "cards.shadow_offset_px", -32, 32)
    cards["roughness_px"] = _integer(cards["roughness_px"], "cards.roughness_px", 0, 16)
    cards["padding_px"] = _integer(cards["padding_px"], "cards.padding_px", 0, 32)

    captions = config.get("captions")
    caption_keys = {"preset", "font_size_px", "height_px", "y_px", "gap_px", "max_width_px", "padding_px", "fill_palette_indexes", "text_palette_keys"}
    if not isinstance(captions, dict) or set(captions) not in (caption_keys, caption_keys | {"preset_asset"}):
        raise ValueError("captions fields do not match the phase 1 caption contract")
    if not isinstance(captions["preset"], str) or not captions["preset"]:
        raise ValueError("captions.preset must be a pinned preset id")
    for key, low, high in (("font_size_px", 18, 200), ("height_px", 40, 300), ("y_px", 0, 1920), ("gap_px", 0, 64), ("max_width_px", 200, 1080), ("padding_px", 0, 48)):
        captions[key] = _integer(captions[key], f"captions.{key}", low, high)
    if captions["font_size_px"] >= captions["height_px"]:
        raise ValueError("captions font must fit inside its chip height")
    if captions["fill_palette_indexes"] != [0, 1, 2, 3]:
        raise ValueError("captions must cycle through the four pinned accent colors")
    if captions["text_palette_keys"] != ["ink", "paper", "paper", "paper"]:
        raise ValueError("captions text colors must be explicit for every accent")
    if "preset_asset" in captions:
        captions["preset_asset"] = _asset_ref(captions["preset_asset"], "captions.preset_asset")
        if captions["preset"] != captions["preset_asset"]["id"]:
            raise ValueError("captions.preset must match its pinned preset asset id")

    decorations = config.get("decorations")
    if decorations is not None:
        if not isinstance(decorations, list) or not 1 <= len(decorations) <= 12:
            raise ValueError("decorations must contain 1..12 pinned assets")
        decoration_ids = set()
        required_blocks = {"mascot_face", "mascot_mouth", "evidence", "logo", "numbers", "caption_chips", "text_safe_area"}
        for index, decoration in enumerate(decorations):
            field = f"decorations[{index}]"
            keys = {"id", "asset", "center_px", "size_px", "intended_use", "safe_area_blocks", "collision_policy", "motion"}
            if not isinstance(decoration, dict) or set(decoration) != keys:
                raise ValueError(f"{field} is invalid")
            if not isinstance(decoration["id"], str) or not _ID.fullmatch(decoration["id"]):
                raise ValueError(f"{field}.id is invalid")
            if decoration["id"] in decoration_ids:
                raise ValueError("decoration ids must be unique")
            decoration_ids.add(decoration["id"])
            decoration["asset"] = _asset_ref(decoration["asset"], f"{field}.asset")
            decoration["center_px"] = _pair(decoration["center_px"], f"{field}.center_px", 0, 1920)
            if decoration["center_px"][0] > 1080:
                raise ValueError(f"{field}.center_px x coordinate exceeds frame width")
            decoration["size_px"] = _integer(decoration["size_px"], f"{field}.size_px", 16, 256)
            if not isinstance(decoration["intended_use"], str) or not decoration["intended_use"]:
                raise ValueError(f"{field}.intended_use must be non-empty")
            blocks = decoration["safe_area_blocks"]
            if (
                not isinstance(blocks, list)
                or len(set(blocks)) != len(blocks)
                or not set(blocks).issubset(required_blocks)
                or not required_blocks.issubset(blocks)
            ):
                raise ValueError(f"{field}.safe_area_blocks must protect every required area")
            if decoration["collision_policy"] != "skip":
                raise ValueError(f"{field}.collision_policy must skip unsafe placements")
            if decoration["motion"] not in {"static", "drift"}:
                raise ValueError(f"{field}.motion must be static or deterministic drift")

    mascot_concept = config.get("mascot_concept")
    if mascot_concept is not None:
        config["mascot_concept"] = _asset_ref(mascot_concept, "mascot_concept")

    layout = config.get("layout")
    required_layout = {"brand_center_px", "topic_center_px", "title_center_px", "content_center_px", "mascot_center_px", "mascot_right_center_px", "aside_center_px", "aside_right_center_px", "cta_center_px", "footer_box", "progress_box"}
    if not isinstance(layout, dict) or set(layout) != required_layout:
        raise ValueError("layout fields do not match paper-v021")
    for key in ("brand_center_px", "topic_center_px", "title_center_px", "content_center_px", "mascot_center_px", "mascot_right_center_px", "aside_center_px", "aside_right_center_px", "cta_center_px"):
        layout[key] = _pair(layout[key], f"layout.{key}", 0, 1920)
    footer = layout["footer_box"]
    if not isinstance(footer, list) or len(footer) != 4:
        raise ValueError("layout.footer_box must contain x, y, width, height")
    layout["footer_box"] = [
        _integer(footer[0], "layout.footer_box[0]", 0, 1080),
        _integer(footer[1], "layout.footer_box[1]", 0, 1920),
        _integer(footer[2], "layout.footer_box[2]", 1, 1080),
        _integer(footer[3], "layout.footer_box[3]", 1, 300),
    ]
    progress = layout["progress_box"]
    if not isinstance(progress, list) or len(progress) != 4:
        raise ValueError("layout.progress_box must contain left, top, right, bottom")
    progress = [
        _integer(progress[0], "layout.progress_box[0]", 0, 1080),
        _integer(progress[1], "layout.progress_box[1]", 0, 1920),
        _integer(progress[2], "layout.progress_box[2]", 0, 1080),
        _integer(progress[3], "layout.progress_box[3]", 0, 1920),
    ]
    if progress[2] <= progress[0] or progress[3] <= progress[1]:
        raise ValueError("layout.progress_box must have positive width and height")
    layout["progress_box"] = progress

    motion = config.get("motion")
    if not isinstance(motion, dict) or set(motion) != {"seed", "mascot_bob_px", "mascot_bob_rate"}:
        raise ValueError("motion fields do not match the phase 1 motion contract")
    motion["seed"] = _integer(motion["seed"], "motion.seed", 0, 2**31 - 1)
    motion["mascot_bob_px"] = _integer(motion["mascot_bob_px"], "motion.mascot_bob_px", 0, 32)
    motion["mascot_bob_rate"] = _number(motion["mascot_bob_rate"], "motion.mascot_bob_rate", 0, 20)

    audio = config.get("audio")
    if not isinstance(audio, dict) or set(audio) != {"bgm_default", "sfx_gain"}:
        raise ValueError("audio fields do not match the phase 1 audio contract")
    if audio["bgm_default"] != "off":
        raise ValueError("BGM remains disabled by default in phase 1")
    audio["sfx_gain"] = _number(audio["sfx_gain"], "audio.sfx_gain", 0, 2)
    return config


def _validate_caption_preset(preset: dict, expected_id: str, version: str) -> dict:
    keys = {"schema_version", "id", "version", "shape", "fill", "text", "border", "shadow", "font", "height_px", "font_size_px", "padding_px"}
    if not isinstance(preset, dict) or set(preset) != keys:
        raise ValueError("Caption preset fields do not match the pinned style contract")
    if (preset["schema_version"], preset["id"], preset["version"]) != (1, expected_id, version):
        raise ValueError("Caption preset identity does not match its pinned path")
    if preset["shape"] != "capsule":
        raise ValueError("Caption preset shape must be capsule")
    preset["fill"] = _color(preset["fill"], "caption_preset.fill")
    preset["text"] = _color(preset["text"], "caption_preset.text")
    border = preset["border"]
    if not isinstance(border, dict) or set(border) != {"color", "width_px"}:
        raise ValueError("Caption preset border is invalid")
    border["color"] = _color(border["color"], "caption_preset.border.color")
    border["width_px"] = _integer(border["width_px"], "caption_preset.border.width_px", 1, 12)
    shadow = preset["shadow"]
    if not isinstance(shadow, dict) or set(shadow) != {"color", "offset_px", "blur_px", "opacity"}:
        raise ValueError("Caption preset shadow is invalid")
    shadow["color"] = _color(shadow["color"], "caption_preset.shadow.color")
    shadow["offset_px"] = _pair(shadow["offset_px"], "caption_preset.shadow.offset_px", -24, 24)
    shadow["blur_px"] = _integer(shadow["blur_px"], "caption_preset.shadow.blur_px", 0, 32)
    shadow["opacity"] = _number(shadow["opacity"], "caption_preset.shadow.opacity", 0, 1)
    font = preset["font"]
    if not isinstance(font, dict) or set(font) != {"id", "version"} or (font["id"], font["version"]) != ("prompt-bold", "v001"):
        raise ValueError("Caption preset must use the pinned Prompt-Bold font")
    preset["height_px"] = _integer(preset["height_px"], "caption_preset.height_px", 40, 300)
    preset["font_size_px"] = _integer(preset["font_size_px"], "caption_preset.font_size_px", 18, 200)
    preset["padding_px"] = _integer(preset["padding_px"], "caption_preset.padding_px", 0, 48)
    if preset["font_size_px"] >= preset["height_px"]:
        raise ValueError("Caption preset font must fit inside its chip height")
    return preset


def load_theme(kit_root: Path, selection: dict | None, *, allow_draft: bool = False) -> dict:
    """Load a pinned theme; draft versions require explicit review-only opt-in."""
    root = Path(kit_root).resolve()
    if selection is None:
        theme_id, version = "base-paper", "v001"
    else:
        if not isinstance(selection, dict) or set(selection) != {"id", "version"}:
            raise ValueError("Theme selection must contain only id and version")
        theme_id, version = selection["id"], selection["version"]
    if not isinstance(theme_id, str) or not _ID.fullmatch(theme_id):
        raise ValueError(f"Invalid theme id: {theme_id!r}")
    if not isinstance(version, str) or not _VERSION.fullmatch(version):
        raise ValueError(f"Invalid theme version: {version!r}")

    index_path = root / "themes" / "index.json"
    index = _read_json(index_path)
    if index.get("schema_version") != 1 or not isinstance(index.get("themes"), list):
        raise ValueError("Unsupported or invalid themes/index.json")
    entries = [entry for entry in index["themes"] if isinstance(entry, dict) and entry.get("id") == theme_id]
    exact = [entry for entry in entries if entry.get("version") == version]
    if not exact:
        raise ValueError(f"Theme version is not pinned in themes index: {theme_id}/{version}")
    if len(exact) != 1:
        raise ValueError(f"Duplicate theme index entry: {theme_id}/{version}")
    status = exact[0].get("status")
    if status not in {"approved", "baseline"} and not (allow_draft and status == "draft"):
        raise ValueError(f"Theme is not approved: {theme_id}/{version}")
    if status == "baseline" and theme_id != "base-paper":
        raise ValueError("Only base-paper may use baseline status")

    theme_path = root / "themes" / theme_id / version / "theme.json"
    theme_path = theme_path.resolve()
    themes_root = (root / "themes").resolve()
    if not theme_path.is_relative_to(themes_root) or not theme_path.is_file():
        raise ValueError(f"Theme file is missing or outside themes/: {theme_id}/{version}")
    schema_path = themes_root / "theme.schema.json"
    schema = _read_json(schema_path)
    if schema.get("schema_version") != 1:
        raise ValueError("Unsupported theme schema")

    config = copy.deepcopy(_read_json(theme_path))
    config = _validate(config, theme_id, version)
    font_rel = _FONT_PATHS[(config["font"]["id"], config["font"]["version"])]
    font_path = (root / font_rel).resolve()
    if not font_path.is_relative_to(root) or not font_path.is_file():
        raise ValueError(f"Pinned theme font is missing: {font_rel.as_posix()}")
    font_hash = hashlib.sha256(font_path.read_bytes()).hexdigest()
    config["font"] = {**config["font"], "path": font_path, "sha256": font_hash}

    resolved_assets = []
    resolved_by_id = {}
    def resolve_once(asset_ref):
        key=(asset_ref["id"],asset_ref["version"])
        if key not in resolved_by_id:
            resolved_by_id[key]=resolve_asset(root,*key,allow_draft=allow_draft)
            resolved_assets.append(resolved_by_id[key])
        return resolved_by_id[key]
    if config["background"]["mode"] == "image":
        asset_ref = config["background"]["asset"]
        asset = resolve_once(asset_ref)
        if not asset["mime"].startswith("image/"):
            raise ValueError("Image backgrounds require an approved image asset")
        config["background"]["resolved_asset"] = asset

    for variant in config.get("background_variants", []):
        asset_ref = variant["asset"]
        asset = resolve_once(asset_ref)
        if not asset["mime"].startswith("image/"):
            raise ValueError("Background variants require image assets")
        variant["resolved_asset"] = asset

    for decoration in config.get("decorations", []):
        asset_ref = decoration["asset"]
        asset = resolve_once(asset_ref)
        if not asset["mime"].startswith("image/"):
            raise ValueError("Decorations require image assets")
        decoration["resolved_asset"] = asset

    preset_ref = config["captions"].get("preset_asset")
    if preset_ref:
        asset = resolve_once(preset_ref)
        if asset["mime"] != "application/json":
            raise ValueError("Caption presets must be JSON data assets")
        preset_data = _validate_caption_preset(_read_json(asset["path"]), preset_ref["id"], preset_ref["version"])
        config["captions"]["resolved_asset"] = asset
        config["captions"]["resolved_preset"] = preset_data

    mascot_ref = config.get("mascot_concept")
    if mascot_ref:
        asset = resolve_once(mascot_ref)
        if asset["mime"] != "image/png":
            raise ValueError("Mascot concepts must be PNG image assets")
        config["resolved_mascot_concept"] = asset
    config["_resolved_assets"] = resolved_assets

    config["_kit_root"] = root
    config["_theme_path"] = theme_path
    config["_theme_index_path"] = index_path.resolve()
    config["_schema_path"] = schema_path.resolve()
    fingerprint = hashlib.sha256()
    fingerprint.update(theme_path.read_bytes())
    fingerprint.update(font_hash.encode())
    for asset in resolved_assets:
        fingerprint.update(asset["sha256"].encode())
        fingerprint.update(asset["metadata_path"].read_bytes())
    fingerprint.update(json.dumps(config, sort_keys=True, ensure_ascii=False, default=str, separators=(",", ":")).encode())
    config["_cache_key"] = fingerprint.hexdigest()
    return config
